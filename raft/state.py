# see: http://ramcloud.stanford.edu/raft.pdf

class State(object):
    def __init__(self):

        # persistent state on all servers
        self.currentTerm = 0
        self.votedFor = None
        self.log = []

        # volatile state on all servers
        self.commitIndex = 0
        self.lastApplied = 0
        
        # volatile state on leaders
        self.nextIndex = {}
        self.matchIndex = {}

        

    
