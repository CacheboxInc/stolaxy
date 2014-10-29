ENTRY_DATA = 0
ENTRY_SNAPSHOT = 1
ENTRY_SKIP = 2

class Entry(object):
    def __init__(self):
        self.entryId = None
        self.data = None

class Consensus(object):
    def __init__(self, serverId, serverAddress):
        self.serverId = serverId
        self.serverAddress = serverAddress

    def init(self):
        pass

    def exit(self):
        pass
    
    def getNextENtry(self, lastEntryId):
        pass

    def getSnapshotStats(self):
        pass

    def beginSnapshot(self):
        pass

    def snapshotDone(self):
        pass

    
