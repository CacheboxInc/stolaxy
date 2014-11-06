from volume import Volume
from filesystem import Filesystem

class Storage(object):
    def __init__(self):
        self.volume = Volume()
        self.filesystem = Filesystem()

    def initialize(self):
        if not self.volume.initialize():
            print 'could not initialize volumes'
            return False

        if not self.filesystem.initialize():
            print 'could not initialize filesystem'
            return False

        print 'storage initialized successfully.'
        return True

        
if __name__ == '__main__':
    Storage().initialize()
