# from ... import utils

if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

    import utils
    # Send normal requests
    utils.replay_sqli_normal_dataset()
    