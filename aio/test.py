import caio
import os
import sys
import time
import random
import zmq

QUEUE_DEPTH = 1024

fd = os.open("/etc/passwd", os.O_RDONLY)

aio = caio.AIO()
aio.io_setup(QUEUE_DEPTH)

ios = []

j = 0

while True:
    cookie = random.randint(0, 100000)
    offset = 0
    if len(ios) < QUEUE_DEPTH:
        buf = aio.io_read(fd, 4096, offset, cookie)
        ios.append(buf)
        print 'submitted: cookie:%s' % (cookie)
        j += 1
    else:
        r = 0
        aio.io_submit()
        while True:
            r = aio.io_getevents()
            for cookie, res, buf in r['reads']:
                print "completed: cookie:%s, bytes read %d" % (cookie, res)
            if r['total'] == len(ios):
                break

        ios = []
        aio.io_reset()
        print 'reaped %d ios. sleeping for %s seconds' % (r['total'], 1)
        time.sleep(1)
