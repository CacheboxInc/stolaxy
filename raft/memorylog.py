from log import *

class MemoryLog(Log):
    def __init__(self):
        Log.__init__(self)
        self.startIndex = 1
        self.entries = []
        self.currentSync = Sync(0)

    def __str__(self):
        return "fix MemoryLog.__str__"

    def append(self, newentries):
        self.entries += newentries # wuhahaha
        
    def getEntry(self, index):
        return self.entries[index - self.startIndex]

    def getLogStartIndex(self):
        return self.startIndex

    def getLastLogIndex(self):
        return self.startIndex + len(self.entries) - 1

    def getSizeBytes(self):
        size = 0
        for entry in self.entries:
            size += len(entry)

        return size

    def takeSync(self):
        other = Sync(self.getLastLogIndex())
        sync = self.currentSync
        self.currentSync = other
        return other

    def truncatePrefix(self, firstIndex):
        if firstIndex > self.startIndex:
            self.entries = self.entries[firstIndex:]

        return

    def truncateSuffix(self, lastIndex):
        if lastIndex < self.startIndex:
            self.entries = []

        elif lastIndex < self.startIndex -1 + len(self.entries):
            self.entries = self.entries[:lastIndex + self.startIndex + 1]

if __name__ == '__main__':
    MemoryLog()
