"""python wait_for_mongodb.py SECONDS

Wait for mongodb to begin listening for connections, or return -1 on timeout.
Ensures tests don't start before MongoDB does. See .travis.yml."""

import socket
import time
from optparse import OptionParser
import sys


def wait_for_mongodb(host, port, seconds):
    start = time.time()
    while time.time() - start < seconds:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            try:
                s.connect((host, port))
                return True
            except (IOError, socket.error):
                time.sleep(0.25)
        finally:
            s.close()

    return False


def parse_args():
    parser = OptionParser(__doc__)
    parser.add_option(
        '-H', '--host', default='localhost',
        help='MongoDB server, default localhost')

    parser.add_option(
        '-p', '--port', default=27017, type=int,
        help='MongoDB port, default 27017')

    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('requires one argument: SECONDS')

    seconds = None
    try:
        seconds = float(args[0])
    except ValueError:
        parser.error('"%s" is not a valid number for SECONDS' % args[0])

    return options.host, options.port, seconds


if __name__ == '__main__':
    host, port, seconds = parse_args()
    if not wait_for_mongodb(host, port, seconds):
        sys.stderr.write('Could not connect to MongoDB\n')
        sys.exit(-1)
