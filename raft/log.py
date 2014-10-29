from metadata import Metadata

class Sync(object):
    def __init__(self, lastIndex):
        self.lastIndex = lastIndex
        self.completed = False

    def wait(self):
        pass

class Log(object):
    def __init__(self):
        self.metadata = Metadata()

    def append(self, entry):
        pass

    def getEntry(self, index):
        pass

    def getLogStartIndex(self):
        pass

    def getLastLogIndex(self):
        pass

    def getSizeBytes(self):
        pass

    def syncComplete(self):
        pass

    def takeSync(self):
        pass

    def truncatePrefix(self, firstIndex):
        pass

    def truncateSuffic(self, lastIndex):
        pass

    def updateMetadata(self):
        pass

    

