import datetime
import random
import threading
import zmq

from config import *
from configuration import SimpleConfiguration
from configuration import Configuration as XConfiguration
from configuration import ConfigurationManager
from consensus import Consensus
from memorylog import MemoryLog
from Raft_pb2 import *

SUCCESS = 0
FAIL = 1
RETRY = 2
NOT_LEADER = 3

class MyMutex(object):
    def __init__(self):
        self.mutex = threading.Lock()

    def acquire(self, blocking = True):
        print 'acquiring mutex'
        self.mutex.acquire(blocking)
        print 'mutex acquired'

    def release(self):
        print 'releasing mutex'
        self.mutex.release()
        print ' mutex released'

class RaftConsensus(Consensus):
    def __init__(self, serverId, serverAddress):
        Consensus.__init__(self, serverId, serverAddress)
        self.mutex = threading.Lock()
#        self.mutex = MyMutex()
        self.stateChanged = threading.Condition(self.mutex)
        self.exiting = False
        self.numPeerThreads = 0
        self.log = MemoryLog()
        self.currentTerm = 0
        self.state = FOLLOWER
        self.lastSnapshotIndex = 0
        self.lastSnapshotTerm = 0
        self.lastSnapshotBytes = 0
        self.commitIndex = 0
        self.leaderId = 0
        self.votedFor = 0
        self.currentEpoch = 0
        self.startElectionAt = datetime.datetime.max
        self.withholdVotesUntil = datetime.datetime.min
        self.leaderDiskThreadWorking = False
        self.logSyncQueued = False
        self.leaderDiskThread = None
        self.timerThread = None
        self.stepDownThread = None
        self.configuration = XConfiguration(serverId, self)
        self.configurationManager = ConfigurationManager(self.configuration)
        self.zctx = zmq.Context()
        rpchandler = self.zctx.socket(zmq.DEALER)
        rpchandler.bind('tcp://%s:5556' % serverAddress)
        self.rpchandler = rpchandler
        t = threading.Thread(target = self.rpcHandlerThread)
        t.start()

    def init(self, serverId):
        self.mutex.acquire()
        self.serverId = serverId
        log = MemoryLog()
        entryId = log.getLogStartIndex()
        while entryId <= log.getLastLogIndex():
            entry = log.getEntry(entryId)
            entryId += 1

        # missing code here. FIX
        if log.metadata.has_current_term():
            self.currentTerm = log.metadata.current_term()
        
        if log.metadata.has_voted_for():
            self.votedFor = log.metadata.voted_for()

        self.updateLogMetadata()
        self.readSnapshot()
        self.stepDown(self.currentTerm)

        self.leaderDiskThread = threading.Thread(target = self.leaderDiskThreadMain)
        self.leaderDiskThread.start()
        self.timerThread = threading.Thread(target = self.timerThreadMain)
        self.timerThread.start()
        self.stepDownThread = threading.Thread(target = self.stepDownThreadMain)
        self.stepDownThread.start()
            
        self.stateChanged.notifyAll()
        self.mutex.release()

    def bootstrapConfiguration(self):
        self.mutex.acquire()
        assert self.currentTerm == 0 and self.log.getLogStartIndex() == 1 and self.log.getLastLogIndex() == 0 \
            and self.lastSnapshotIndex == 0

        self.stepDown(1)
        entry = Entry()
        entry.term = 1
        entry.type = CONFIGURATION
        server = Server()
        server.server_id = self.serverId
        server.address = self.serverAddress
        self.append(entry)
        self.mutex.release()
        pass

    def getLastCommittedId(self):
        pass

    def getLeaderHint(self):
        pass

    def getNextEntry(self, lastEntryId):
        pass

    def getSnapshotStats(self):
        pass

    def handleAppendEntries(self):
        assert 0
        pass

    def handleAppendSnapshotChunk(self):
        pass

    def handleRequestVote(self):
        assert 0
        pass

    def replicate(self):
        pass

    def setConfiguration(self, oldId, _members):
        print 'changing raft configuration to: %s' % _members
        self.mutex.acquire()
        
        members = []
        for a,p,s in _members:
            if s != self.serverId:
                members.append((a, p, s))
            
        nextConfiguration = SimpleConfiguration()
        for address, port, serverId in members:
            server = Server()
            server.server_id = int(serverId)
            server.address = address
            nextConfiguration.servers.extend([server])

        if self.state != LEADER:
            self.mutex.release()
            return False

#        if self.configuration.id != oldId or self.configuration.state != STABLE:
        if self.configuration.state != STABLE:
            self.mutex.release()
            return False

        term = self.currentTerm
        self.configuration.setStagingServers(members)
        self.stateChanged.notifyAll()
        self.currentEpoch += 1
        epoch = self.currentEpoch
        checkProgressAt = datetime.datetime.now() + datetime.timedelta(seconds = ELECTION_TIMEOUT_SECONDS)

        while True:
            if self.exiting or term != self.currentTerm:
                self.mutex.release()
                return False

            if self.configuration.stagingAll('isCaughtUp'):
                break

            if datetime.datetime.now() >= checkProgressAt:
                if self.configuration.stagingMin('getLastAckEpoch') < epoch:
                    self.configuration.resetStagingServers()
                    self.stateChanged.notifyAll()
                    self.mutex.release()
                    return False

                else:
                    self.currentEpoch += 1
                    epoch = self.currentEpoch
                    checkProgressAt = datetime.datetime.now() + datetime.timedelta(seconds = ELECTION_TIMEOUT_SECONDS)
                    
            self.stateChanged.wait(ELECTION_TIMEOUT_SECONDS)
        
        newConfiguration = Configuration()
        newConfiguration.prev_configuration = self.configuration.description.prev_configuration
        newConfiguration.next_configuration = nextConfiguration

        entry = Entry()
        entry.type = CONFIGURATION
        entry.configuration = newConfiguration
        result = self.replicateEntry(entry)

        if result != True:
            self.mutex.release()
            return False
        
        self.mutex.release()
        return True
        
    def beginSnapshot(self):
        pass

    def snapshotDone(self):
        pass

# private functions

    def leaderDiskThreadMain(self):
        self.mutex.acquire()
        while not self.exiting:
            if self.state == LEADER and self.logSyncQueued:
                term = self.currentTerm
                sync = self.log.takeSync()
                self.logSyncQueued = False
                self.leaderDiskThreadWorking = True
                self.mutex.release()
                sync.wait()
                self.leaderDiskThreadWorking = False
                
                if self.state == LEADER and self.currentTerm == term:
                    self.advanceCommittedId()

                self.log.syncComplete()
                self.mutex.acquire()
            self.stateChanged.wait()
        self.mutex.release()
        pass

    def timerThreadMain(self):
        self.mutex.acquire()
        while not self.exiting:
            #print 'timer: %s %s' % (datetime.datetime.now(), self.startElectionAt)

            if datetime.datetime.now() >= self.startElectionAt:
                self.startNewElection()
            else:
                wait = (self.startElectionAt - datetime.datetime.now()).seconds
                self.stateChanged.wait(wait)
        pass

    def peerThreadMain(self, peer):
        self.mutex.acquire()

        while not peer.exiting:
            now = datetime.datetime.now()
            waitUntil = datetime.datetime.min

            if peer.backoffUntil > now:
                waitUntil = peer.backoffUntil
            else:
                if self.state == FOLLOWER:
                    waitUntil = datetime.datetime.max
                elif self.state == CANDIDATE:
                    if not peer.requestVoteDone:
                        self.requestVote(peer)
                    else:
                        waituntil = datetime.datetime.max
                elif self.state == LEADER:
                    if peer.getLastAgreeIndex() < self.log.getLastLogIndex() or peer.nextHeartbeatTime < now:
                        self.appendEntries(peer)
                    else:
                        waitUntil = peer.nextHeartbeatTime
                
            if datetime.datetime.now() > waitUntil:
                #delta = (datetime.datetime.now() - waitUntil).seconds
                delta = 2
            else:
                delta = (waitUntil - datetime.datetime.now()).seconds

            print 'peerThread (%s): sleeping for %s seconds' % (peer.address, delta)
            self.stateChanged.wait(delta)

        self.numPeerThreads -= 1
        self.stateChanged.notifyAll()
        self.mutex.release()
        pass

    def stepDownThreadMain(self):
        pass

    def rpcHandlerThread(self):
        handler = self.rpchandler
        while True:
            message = handler.recv()
            entry = Entry()
            entry.ParseFromString(message)
            print 'message received'
            print entry
        
    def advanceCommittedId(self):
        pass

    def append(self, entries):
        if not isinstance(entries, list):
            entries = [entries, ]

        for entry in entries:
            assert entry.term != 0

        first, last = self.log.append(entries)

        if self.state == LEADER:
            self.logSyncQueued = True
        else:
            sync = self.log.takeSync()
            sync.wait()
            self.log.syncComplete()

        index = first
        for entry in entries:
            if entry.type == CONFIGURATION:
                self.configurationManager.add(index, entry.configuration)
                pass
            index += 1

        self.stateChanged.notify_all()
        pass

    def appendEntries(self, peer):
        lastLogIndex = self.log.getLastLogIndex()
        prevLogIndex = peer.nextIndex - 1
        assert prevLogIndex <= lastLogIndex
        
        if peer.nextIndex < self.log.getLogStartIndex():
            self.appendSnapshotChunk(peer)
            return

        if prevLogIndex >= self.log.getLogStartIndex():
            prevLogTerm = self.log.getEntry(prevLogIndex).term
        elif prevLogIndex == 0:
            prevLogTerm = 0
        elif prevLogIndex == self.lastSnapshotIndex:
            prevLogTerm = self.lastSnapshotTerm
        else:
            self.appendSnapshotChunk(peer)

        request = AppendEntries.Request()
        request.server_id = self.serverId
        request.recipient_id = int(peer.serverId)
        request.term = self.currentTerm
        request.prev_log_term = prevLogTerm
        request.prev_log_index = prevLogIndex

        numEntries = 0
        if not peer.forceHeartbeat:
            entryId = peer.nextIndex
            while entryId <= lastLogIndex:
                entry = self.log.getEntry(entryId)
                request.append([entry])
                entryId += 1
                numEntries += 1

        request.commit_index = min(self.commitIndex, prevLogIndex + numEntries)
        print 'sending APPEND_ENTRIES to %s' % peer.address
        response = peer.callRPC(APPEND_ENTRIES, request)
        pass

    def appendSnapshotChunk(self):
        assert 0
        pass

    def becomeLeader(self):
        assert self.state == CANDIDATE
        print 'becoming leader for term: %d' % self.currentTerm
        self.state = LEADER
        self.leaderId = self.serverId
        self.startElectionAt = datetime.datetime.max
        self.withholdVotesUntil = datetime.datetime.max
        self.configuration.forEach('beginLeadership')
        
        entry = Entry()
        entry.term = self.currentTerm
        entry.type = NOOP
        self.append([entry, ])
        self.interruptAll()

        pass

    def discardUnneededEntries(self):
        pass

    def getLastLogTerm(self):
        pass

    def interruptAll(self):
        pass

    def readSnapshot(self):
        pass

    def replicateEntry(self):
        pass

    def requestVote(self, peer):
        request = RequestVote()
        request.server_id = self.serverId
        request.recipient_id = peer.serverId
        request.term = self.currentTerm
        request.last_log_term = self.getLastLogTerm()
        request.last_log_index = self.log.getLastLogIndex()
        
        print 'requestVote start'
        start = datetime.datetime.now()
        epoch = self.currentEpoch()
        response = peer.callRPC(REQUEST_VOTE, request)
        
        if not response:
            print 'rpc failure'
            peer.backoffUntil = start + RPC_FAILURE_BACKOFF_MS
            return

        if self.currentTerm != request.term or self.state != CANDIDATE or peer.exiting:
            return

        if response.term > self.currentTerm:
            self.stepDown(response.term)
        else:
            peer.requestVoteDone = True
            peer.lastAckEpoch = epoch
            self.stateChanged.notifyAll()
            
            if response.granted:
                peer.haveVote_ = True
                print 'gote vote for term %d' % self.currentTerm
                if self.configuration.quorumAll('haveVote'):
                    self.becomeLeader()
            else:
                print 'vote not granted'

        pass

    def setElectionTimer(self):
        ms = random.randrange(ELECTION_TIMEOUT, ELECTION_TIMEOUT * 2)
        self.startElectionAt = datetime.datetime.now() + datetime.timedelta(seconds = ms/1000)
        print 'will become candidate in %d ms at %s' % (ms, self.startElectionAt)
        self.stateChanged.notifyAll()
        pass

    def startNewElection(self):
        print ('startNewElection (%s)' % self.state).center(80, '-')
        # if self.configuration.id == None:
        #     self.setElectionTimer()
        #     return

        if self.state == FOLLOWER:
            print 'running for election in term: %d' % (self.currentTerm + 1)

        self.currentTerm += 1
        self.state = CANDIDATE
        self.leaderId = 0
        self.votedFor = self.serverId
        self.setElectionTimer()
        self.configuration.forEach('beginRequestVote')
        self.updateLogMetadata()
        self.interruptAll()
        if self.configuration.quorumAll('haveVote'):
            print 'becomeleader'.center(80, '#')
            self.becomeLeader()
        else:
            print 'no quorum!'.center(80, '#')

        pass

    def stepDown(self, newTerm):
        assert self.currentTerm <= newTerm
        if self.currentTerm < newTerm:
            self.currentTerm = newTerm
            self.leaderId = 0
            self.votedFor = 0
            self.updateLogMetadata()
            
        self.state = FOLLOWER
        if self.startElectionAt == datetime.datetime.max:
            self.setElectionTimer()

        if self.withholdVotesUntil == datetime.datetime.max:
            self.withholdVotesUntil = datetime.datetime.min

        self.interruptAll()

        while self.leaderDiskThreadWorking:
            time.sleep(1)
            
        if self.logSyncQueued:
            sync = self.log.takeSync()
            sync.wait()
            self.log.syncComplete()
            self.logSyncQueued = False

        pass

    def updateLogMetadata(self):
        self.log.metadata.set_current_term(self.currentTerm)
        self.log.metadata.set_voted_for(self.votedFor)
        self.log.updateMetadata()

    def upToDateLeader(self):
        pass

if __name__ == '__main__':
    rc = RaftConsensus(1, '127.0.0.1')
    rc.bootstrapConfiguration()
    rc.init(1)
