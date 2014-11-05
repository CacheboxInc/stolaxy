from volume import Volume
from filesystem import Filesystem

class Storage(object):
    def __init__(self):
        self.volume = Volume()
        self.filesystem = Filesystem()

    def initialize(self):
        self.volume.initialize()
        self.filesystem.initialize()

        print 'storage initialized successfully.'
        
if __name__ == '__main__':
    Storage().initialize()
