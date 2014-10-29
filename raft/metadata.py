import shelve

class Metadata(object):
    def __init__(self, filename = '/tmp/raft.md'):
        self.filename = filename
        self.md = shelve.open(filename)

    def has_current_term(self):
        return self.md.has_key('currentTerm')

    def has_voted_for(self):
        return self.md.has_key('votedFor')

    def set_current_term(self, currentTerm):
        self.md['currentTerm'] = currentTerm

    def set_voted_for(self, votedFor):
        self.md['votedFor'] = votedFor

    def current_term(self):
        return self.md['currentTerm']

    def voted_for(self):
        return self.md['votedFor']

    def updateMetadata(self):
        self.md.sync()
