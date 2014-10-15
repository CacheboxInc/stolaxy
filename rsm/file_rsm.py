"""
Implements a file object which is RSM friendly.
"""

import os

class FileObject(object):
    def __init__(self):
        pass

    def open(self, name):
        self.f = os.open(name, os.O_RDWR|os.O_CREAT)
        return self.f
        
    def read(self, size=4096):
        return os.read(self.f, size)

    def write(self, data):
        return os.write(self.f, data)

    def close(self):
        return os.close(self.f)
