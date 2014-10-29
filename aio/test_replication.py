import caio
import getopt
import os
import sys
import threading
import time
import random
import zmq

from Raft_pb2 import *

QUEUE_DEPTH = 1024

fd = os.open("/etc/passwd", os.O_RDONLY)


URL = 'tcp://%s:5556'

def do_work(context, requester):

    aio = caio.AIO()
    aio.io_setup(QUEUE_DEPTH)
    ios = []
    data = 'A' * 4096

    while True:
        cookie = random.randint(0, 100000)
        offset = 0
        if len(ios) < QUEUE_DEPTH:

            entry = Entry()
            entry.term = 2
            entry.type = DATA
            entry.data = data
            requester.send(entry.SerializeToString())
#            response = requester.recv()

            buf = aio.io_read(fd, 4096, offset, cookie)
            ios.append(buf)
#            print 'submitted: cookie:%s' % (cookie)
        else:
            r = 0
            aio.io_submit()
            while True:
                r = aio.io_getevents()
                # for cookie, res, buf in r['reads']:
                #     print "completed: cookie:%s, bytes read %d" % (cookie, res)
                if r['total'] == len(ios):
                    break

            ios = []
            aio.io_reset()
#            print 'reaped %d ios. sleeping for %s seconds' % (r['total'], 1)



def do_client(server):
    print 'starting client. connecting to server at: %s' % server
    ctx = zmq.Context()
    requester = ctx.socket(zmq.DEALER)
    requester.connect(server)
    t = threading.Thread(target = do_work, kwargs = {'context':ctx, 'requester':requester})
    t.start()
    pass

def do_server(server):
    print 'starting server at: %s' % server
    ctx = zmq.Context()
    responder = ctx.socket(zmq.DEALER)
    responder.bind(server)
    while True:
        message = responder.recv()
        entry = Entry()
        entry.ParseFromString(message)
        print 'message received'

    pass


def usage():
    print 'python tr.py [--server=<ip:port>] [--client]'
    sys.exit(2)

def main():
    server = None
    client = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "", 
                                   ["server=", 
                                    "client",
                                    ])

    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)
    for o, a in opts:
        if o in ("--server"):
            server = a
        elif o in ("--client"):
            client = True

    if client and server is None:
        usage()

    server = URL % server

    if client:
        do_client(server)

    else:
        do_server(server)

if __name__ == '__main__':
    main()
