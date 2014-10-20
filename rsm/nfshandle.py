"""
implements the counterparts for nfs server HardHandle
"""

from ctypes import *
import os
import sys

sys.path.append('../concoord-1.1.0')

cdll.LoadLibrary("libc.so.6")
libc = CDLL("libc.so.6")

class NFSHandle(object):
    def create(self, fullfile):
        fd = os.open(fullfile, os.O_CREAT)
        os.close(fd)
        return 0
    
    def mkdir(self, fullfile):
        return os.mkdir(fullfile)

    def write(self, filename, data, offset):
        fd = os.open(filename, os.O_RDWR)
        size = libc.pwrite(fd, data, len(data), offset)
        os.close(fd)
        return size
