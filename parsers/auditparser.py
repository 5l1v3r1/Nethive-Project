from utils import tail
import os
from ctypes import *

def main():
    AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH")

    logfile = open(AUDIT_LOG_PATH, 'r')
    loglines = tail(logfile)

    lib = cdll.LoadLibrary("./parsers/lib/auparse.so")

    print("[*] Starting AuditParser Engine...")

    # Parameters: debug bool, in string, interpret bool, idLookup bool, format string
    # print(lib.Parse(False, """type=SYSCALL msg=audit(1515619721.392:106081): arch=c000003e syscall=59 success=yes exit=0 a0=55df1048ec88 a1=55df1048ec38 a2=55df1048ec58 a3=1 items=2 ppid=27851 pid=27854 auid=4294967295 uid=0 gid=0 euid=0 suid=0 fsuid=0 egid=0 sgid=0 fsgid=0 tty=(none) ses=4294967295 comm="grep" exe="/bin/grep" key=65786563013634626974""", True, True, "yaml"))

if __name__ == '__main__':
    main()