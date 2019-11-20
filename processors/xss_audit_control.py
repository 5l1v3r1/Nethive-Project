import socket
import threading
import json
from storage.redistor import RedisClient
from dateutil.parser import parse
import traceback
import time
import os
from utils import decode_deeply
from processors import xss_watcher

# import signal

AUDIT_CONTROL_HOST = os.getenv("AUDIT_CONTROL_HOST")
AUDIT_CONTROL_PORT = int(os.getenv("AUDIT_CONTROL_PORT"))

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((AUDIT_CONTROL_HOST, AUDIT_CONTROL_PORT))
server.listen(5)

redis = RedisClient.getInstance()

def keyboardInterruptHandler(signal, frame):
    server.close()

def parse_returned_sql_rows(raw_rows):
    raw_rows = list(filter(None, raw_rows.split("\n")))
    headers = raw_rows[0].split(",")
    responses = []
    for row in raw_rows[1:]:
        rsp_obj = {}
        row_split = row.split(",")
        for i in range(len(headers)):
            rsp_obj[headers[i]] = normalize_json_quote_problem(row_split[i])
        responses.append(rsp_obj)
    return responses

def parse_mysql_beat_packet(beat_packet):
    try:
        d = parse(beat_packet['@timestamp'])
        beat_packet = {
            'timestamp': int(time.mktime(d.timetuple())),
            'conn_stat': {
                'from_ip': beat_packet['client']['ip'],
                'from_port': beat_packet['client']['port'],
                'bytes': beat_packet['client']['bytes'],
            },
            'sql_method': beat_packet['method'],
            'sql_data': {
                'db_object': beat_packet['path'],
                'query': beat_packet['query'],
                'response': parse_returned_sql_rows(beat_packet['response']),
            },
            'sql_stat': {
                'affected_rows': beat_packet['mysql']['affected_rows'],
                'insert_id': beat_packet['mysql']['insert_id'],
                'num_fields': beat_packet['mysql']['num_fields'],
                'num_rows': beat_packet['mysql']['num_rows'],
            },
            'status': beat_packet['status']
        }
        return beat_packet
    except Exception as e:
        print(traceback.format_exc())

def restructure_for_auditor(package):
    try:
        package = {
            "req_packet": json.loads(package['req_packet']),
            "res_body": package['res_body'].encode(),
            "time": int(time.time())
        }
    except Exception as e:
        print(traceback.format_exc())
    return package

def add_sql_to_inspection_package(package, beat_data):
    try:
        package = restructure_for_auditor(package)
        package['req_packet']['sql_response'] = beat_data['sql_data']['response']
    except Exception as e:
        print(traceback.format_exc())
    return package

def get_flow_time_average():
    # TODO: write an algorithm to calculate time between http and sql dynamically
    return 1.0

def normalize_json_quote_problem(the_data):
    """
        Setiap data yang mengandung double-quote (") pada database, ketika masuk ke packetbeat, double-quote tersebut akan menjadi double double-quote (""). Fungsi ini berguna untuk melakukan normalisasi terhadap anomali tersebut.

        Algorithm:
        1. remove wrapping double quote (at start and end of the data)
        2. for each of the remaining double quotes, remove half of it.
            Example:
                "nama saya adalah """"""ANDO""""""" | 6 double quotes before ANDO (exclude the double quotes in the beginning of the string), 7 double quotes after ANDO
                1 -> nama saya adalah """"""ANDO"""""" | 6 double quotes before ANDO, 6 double quotes after ANDO
                2 -> nama saya adalah \"\"\"ANDO\"\"\" | 6/2 double quotes before and after ANDO (remove the backslashes)
    """
    # --1.
    if the_data.startswith('"') and the_data.endswith('"'):
        the_data = the_data[1:-1]
        # --2.
        the_data = the_data.replace('""', '"')
    return the_data

def find_related_redis_data(package_identifiers):
    for the_pack in package_identifiers:
        timestamp, package_id = the_pack
        package_id =  int(float(package_id))
        package = redis.rs_get_all_pop_one("audit:{}".format(package_id))
        yield package
        
def handle_client_connection(client_socket):
    while True:
        request = client_socket.recv(16384)

        if not request:
            print("[Audit Control] Client has disconnected")
            client_socket.close()
            break
        try:
            lower_boundary = int(int(time.time()) - get_flow_time_average())
            upper_boundary = int(int(time.time()) + get_flow_time_average())
            package_identifiers = redis.ts_get_by_range(RedisClient.TS_STORE_KEY, lower_boundary, upper_boundary)

            beat_data = json.loads(request.decode("utf-8"))

            if beat_data['type'] == 'mysql':
                beat_data = parse_mysql_beat_packet(beat_data)
                if beat_data:
                    for package in find_related_redis_data(package_identifiers):
                        package = add_sql_to_inspection_package(decode_deeply(package), beat_data)
                        xss_watcher.domparse(package, False) # inspect request data ALONG WITH sql response
            elif beat_data['type'] == 'http':
                package = restructure_for_auditor(beat_data)
                xss_watcher.domparse(package, False) # inspect request data WITHOUT sql response
                pass
        except Exception as e:
            print(traceback.format_exc())
            pass

def start():
    # --- Set signal handlers
    # signal.signal(signal.SIGINT, keyboardInterruptHandler)

    while True:
        client_sock, address = server.accept()
        print('[Audit Control] Accepted connection from {}:{}'.format(address[0], address[1]))
        client_handler = threading.Thread(
            target=handle_client_connection,
            args=(client_sock,)
        )
        client_handler.start()

    server.close()

def run():
    print('[Audit Control] Listening on {}:{}'.format(AUDIT_CONTROL_HOST, AUDIT_CONTROL_PORT))
    start()