# see: http://ramcloud.stanford.edu/raft.pdf

import datetime
import threading
import zmq

from config import *

class Server(object):
    def __init__(self, serverId):
        self.serverId = serverId
        self.state = FOLLOWER
        self.electiontimeout = ELECTION_TIMEOUT

    def beginRequestVote(self):
        pass

    def beginLeadership(self):
        pass

    def init(self):
        pass

    def exit(self):
        pass

    def getLastAckEpoch(self):
        pass

    def getLastAgreeIndex(self):
        pass
    
    def haveVote(self):
        pass

    def interrupt(self):
        pass

    def isCaughtUp(self):
        pass

    def scheduleHeartbeat(self):
        pass


class LocalServer(Server):
    def __init__(self, serverId, consensus):
        Server.__init__(self, serverId)
        self.lastSyncedIndex = 0
        self.consensus = consensus

    def beginRequestVote(self):
        pass

    def beginLeadership(self):
        self.lastSyncedIndex = self.consensus.log.getLastLogIndex()

    def exit(self):
        pass

    def getLastAckEpoch(self):
        return self.consensus.currentEpoch

    def getLastAgreeIndex(self):
        return self.lastSyncedIndex

    def isCaughtUp(self):
        return True

    def haveVote(self):
        return self.consensus.votedFor == self.serverId

class Peer(Server):
    def __init__(self, serverId, address, consensus):
        Server.__init__(self, serverId)
        self.consensus = consensus
        self.exiting = False
        self.requestVoteDone = False
        self.forceHeartbeat = False
        self.nextIndex = consensus.log.getLastLogIndex() + 1
        self.lastAgreeIndex = 0
        self.lastAckEpoch = 0
        self.nextHeartBeatTime = datetime.datetime.min
        self.backoffUntil = datetime.datetime.min
        self.thread = None
        self.haveVote_ = False
        self.isCaughtUp_ = False
        self.lastSnapshotIndex = 0
        self.address = address
        self.lastCatchUpIterationMs = 0
        self.thisCatchUpIterationStart = datetime.datetime.now()
        self.thisCatchUpIterationGoalId = 0

        requester = consensus.zctx.socket(zmq.REQ)
        requester.connect('tcp://%s:5556' % (self.address))
        self.requester = requester

        # the raft leader sends requests to raft peers

    def callRPC(self, request, mutex):
        self.requester.send(request.SerializeToString())
        mutex.release()
        response = self.requester.recv()
        mutex.acquire()
        return response

    def startThread(self):
        self.thisCatchUpIterationStart = datetime.datetime.now()
        self.thisCatchUpIterationGoalId = self.consensus.log.getLastLogIndex()
        self.consensus.numPeerThreads += 1
        thread = threading.Thread(target = self.consensus.peerThreadMain, kwargs = {'peer':self})
        thread.start()

    def beginRequestVote(self):
        self.requestVoteDone = False
        self.haveVote_ = False

    def haveVote(self):
        return self.haveVote_
        

    def beginLeadership(self):
        self.nextIndex = self.consensus.log.getLastLogIndex() + 1
        self.lastAgreeIndex = 0
        self.forceHeartbeat = True
        self.snapshotFile.reset()
        self.snapshotFileOffset = 0
        self.lastSnapshotIndex = 0

    def exit(self):
        self.exiting = True

    def getLastAckEpoch(self):
        return self.lastAckEpoch

    def getLastAgreeIndex(self):
        return self.lastAgreeIndex

    def isCaughtUp(self):
        return self.isCaughtUp_

    def scheduleHeartbeat(self):
        self.nextHeartbeatTime = datetime.datetime.now()
