"""
implements the counterparts for nfs server HardHandle
"""

import os
import sys

sys.path.append('../concoord-1.1.0')

class NFSHandle(object):
    def create(self, fullfile):
        fd = os.open(fullfile, os.O_CREAT)
        os.close(fd)
        return 0
    
    def mkdir(self, fullfile):
        return os.mkdir(fullfile)
