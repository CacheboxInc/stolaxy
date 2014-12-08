import caio
import os
import sys
import time
import random
import chardet
import mmap
import gc
from concurrent.futures import ProcessPoolExecutor as Pool

QUEUE_DEPTH = 128
NR_THREADS = 32

def thr_func(i):
    print "starting thread %s" % i
    fd = os.open("/mnt/xfs/test_file", os.O_RDONLY)
    aio = caio.AIO()
    aio.io_setup(QUEUE_DEPTH)
    ios = []
    while True:
        gc.collect()
        if len(ios) < QUEUE_DEPTH:
            xid = random.randint(0, 100000000)
            offset = random.randint(0, 10 << 30) & ~(4095)
            buf = aio.io_read(fd, 4096, offset, xid)
            ios.append(buf)
        else:
            r = 0
            aio.io_submit()
            while True:
                r = aio.io_getevents()
                for xid, res, buf in r['reads']:
                    pass
                    #print "completed: xid:%s, bytes read %d %s " % (xid, res, buf)
                if r['total'] == len(ios):
                    break

            ios = []
            aio.io_reset()

    os.close(fd)

def test1() :
    readers = []

    pool = Pool(max_workers = NR_THREADS)

    for t in xrange(0, NR_THREADS):
        reader = pool.submit(thr_func, (t,))
        readers.append(reader)

def test2():
    fd = os.open("/mnt/xfs/test_file", os.O_RDONLY|os.O_DIRECT)
    aio = caio.AIO()
    aio.io_setup(QUEUE_DEPTH)
    xid = random.randint(0, 100000000)
    offset = 4096
    buf = aio.io_read(fd, 4096, offset, xid)
    aio.io_submit()
    while True:
        print "test 1"
        r = aio.io_getevents()
        for xid, res, buf in r['reads']:
            print "completed: xid:%s, bytes read %d" % (xid, res)
            print buf
            print len(buf)
        if r['total'] == 1:
            break

    os.close(fd)

    fd = os.open("/mnt/xfs/test_file", os.O_RDONLY)
    aio = caio.AIO()
    aio.io_setup(QUEUE_DEPTH)
    xid = random.randint(0, 100000000)
    offset = 4091
    buf = aio.io_read(fd, 4091, offset, xid)
    aio.io_submit()
    while True:
        print "test 2"
        r = aio.io_getevents()
        for xid, res, buf in r['reads']:
            print "completed: xid:%s, bytes read %d" % (xid, res)
            print buf
            print len(buf)
        break

    os.close(fd)


    aio = caio.AIO()
    aio.io_setup(QUEUE_DEPTH)
    fd = os.open("/etc/passwd", os.O_RDWR)
    data = os.read(fd, 1192)
    os.close(fd)
    fd2 = os.open("/mnt/xfs/t1", os.O_RDWR)
    xid = random.randint(0, 100000000)
    buf = aio.io_write(fd2, data, len(data), offset, xid)
    fd = os.open("/mnt/xfs/t2", os.O_RDWR|os.O_DIRECT)
    xid = random.randint(0, 100000000)
    data = 'b' * 4096
    buf = aio.io_write(fd, data, len(data), 0, xid)
    data = "asas2132134d\n"
    fd1 = os.open("/mnt/xfs/t3", os.O_RDWR)
    xid = random.randint(0, 100000000)
    buf = aio.io_write(fd1, data, len(data), offset, xid)
    aio.io_submit()
    ret = 0
    print "test 3"
    while True:
        r = aio.io_getevents()
        ret += r['total']
        for xid, res in r['writes']:
            print "completed: xid:%s, bytes written %d" % (xid, res)
        if ret == 2:
            break

    aio.io_reset()
    os.close(fd)
    os.close(fd1)
    os.close(fd2)

if __name__ == "__main__":
    test1()
