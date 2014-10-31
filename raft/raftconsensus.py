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

    def handleAppendEntries(self, request):
        self.mutex.acquire()
        assert not self.exiting

        response = AppendEntries.Response()
        response.opcode = APPEND_ENTRIES
        response.term = self.currentTerm
        response.success = False
        
        if request.term < self.currentTerm:
            self.mutex.release()
            return response

        if request.term > self.currentTerm:
            print 'caller %s has newer term, updating from %s to %s' % (request.server_id, self.currentTerm, request.term)
            response.term = request.term
        
        self.stepDown(request.term)
        self.setElectionTimer()
        self.withholdVotesUntil = datetime.datetime.now() + datetime.timedelta(ELECTION_TIMEOUT_SECONDS)
        
        if self.leaderId == 0:
            self.leaderId = request.server_id
        else:
            assert self.leaderId == request.server_id

        if request.prev_log_index > self.log.getLastLogIndex():
            print 'rejecting append entries RPC. would leave a gap'
            self.mutex.release()
            return response

        if request.prev_log_index >= self.log.getLogStartIndex() and \
                self.log.getEntry(request.prev_log_index).term != request.prev_log_term:
            print 'rejecting append entries RPC. terms dont agree'
            self.mutex.release()
            return response

        response.success = True
        
        entries = []
        entryId = request.prev_log_index
        for entry in request.entries:

            entryId += 1
            if entryId < self.log.getLogStartIndex():
                assert 0, 'Handle this!'
                continue

            if self.log.getLastLogIndex() >= entryId:
                assert 0, 'Handle this!'
                if self.log.getEntry(entryId).term == entry.term:
                    continue

                assert self.commitIndex < entryId
                self.log.truncateSuffix(entryId - 1)
                self.configurationManager.truncateSuffix(entryId - 1)
            
            entries.append(entry)

        if len(entries) > 0:
            self.append(entries)

        if self.commitIndex < request.commit_index:
            self.commitIndex = request.commit_index
            assert self.commitIndex <= self.log.getLastLogIndex()
            self.stateChanged.notify_all()

        self.mutex.release()
        return response

    def handleAppendSnapshotChunk(self):
        pass

    def handleRequestVote(self, request):
        print 'handleRequestVote: %s' % request
        self.mutex.acquire()
        response = RequestVote.Response()
        if self.withholdVotesUntil > datetime.datetime.now():
            print 'rejecting request vote as I am withholding votes'
            response.term = self.currentTerm
            response.granted = False
            self.mutex.release()
            return

        if request.term > self.currentTerm:
            print 'caller has new term, updating'
            self.stepDown(request.term)

        lastLogIndex = self.log.getLastLogIndex()
        lastLogTerm = self.getLastLogTerm()
        logIsOk = request.last_log_term > lastLogTerm or \
            (request.last_log_term == lastLogTerm and \
                 request.last_log_index >= lastLogIndex)

        if request.term == self.currentTerm and logIsOk and self.votedFor == 0:
            print 'voting for %s in term %s' % (request.server_id, self.currentTerm)
            self.stepDown(self.currentTerm)
            self.setElectionTimer()
            self.votedFor = request.server_id
            self.updateLogMetadata()

        response.term = self.currentTerm
        response.granted = request.term == self.currentTerm and self.votedFor == request.server_id
        self.mutex.release()
        pass

    def replicate(self):
        pass

    def setConfiguration(self, oldId, members):
        self.mutex.acquire()
        if self.state != LEADER:
            self.mutex.release()
            return False
        
        print 'changing raft configuration to: %s' % members
        nextConfiguration = SimpleConfiguration()
        for address, port, serverId in members:
            server = Server()
            server.server_id = int(serverId)
            server.address = address
            nextConfiguration.servers.extend([server])

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
                    print self.configuration.stagingMin('getLastAckEpoch'), epoch
                    self.configuration.resetStagingServers()
                    self.stateChanged.notifyAll()
                    self.mutex.release()
                    return False

                else:
                    self.currentEpoch += 1
                    epoch = self.currentEpoch
                    checkProgressAt = datetime.datetime.now() + datetime.timedelta(seconds = ELECTION_TIMEOUT_SECONDS)
                    
            self.stateChanged.wait(ELECTION_TIMEOUT_SECONDS)

        print 'NEW CONFIGURATION'.center(80, '#')
        newConfiguration = Configuration()
        newConfiguration.prev_configuration.CopyFrom(self.configuration.description.prev_configuration)
        newConfiguration.next_configuration.CopyFrom(nextConfiguration)

        entry = Entry()
        entry.type = CONFIGURATION
        entry.configuration.CopyFrom(newConfiguration)
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
                    self.configuration.localServer.lastSyncedIndex = sync.lastIndex
                    self.advanceCommittedId()

                self.log.syncComplete()
                self.mutex.acquire()
            self.stateChanged.wait()
        self.mutex.release()
        pass

    def timerThreadMain(self):
        self.mutex.acquire()
        while not self.exiting:
            if datetime.datetime.now() >= self.startElectionAt:
                self.startNewElection()
            else:
                wait = (self.startElectionAt - datetime.datetime.now()).seconds
                wait = max(0.01, wait)
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
                    print 'CANDIDATE'.center(80, '#')
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

            delta = max(1, delta)
            #print 'peerThread (%s): sleeping for %s seconds' % (peer.address, delta)
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
            
            rpc = RPC()
            rpc.ParseFromString(message)
            response = None

            if rpc.opcode == APPEND_ENTRIES:
                ae = AppendEntries.Request()
                ae.ParseFromString(message)
                response = self.handleAppendEntries(ae)
            elif rpc.opcode == REQUEST_VOTE:
                rv = RequestVote.Request()
                rv.ParseFromString(message)
                response = self.handleRequestVote(rv)
            else:
                print 'WARNING: received unknown RPC with opcode: %s' % rpc.opcode

            if response:
                handler.send(response.SerializeToString())
        
    def advanceCommittedId(self):
        if self.state != LEADER:
            return

        newCommittedId = self.configuration.quorumMin('getLastAgreeIndex')
        print 'advanceCommittedId ', newCommittedId
        if self.commitIndex >= newCommittedId:
            print '2' * 80
            return

        assert newCommittedId >= self.log.getLogStartIndex()
        if self.log.getEntry(newCommittedId).term != self.currentTerm:
            print '3' * 80
            return

        self.commitIndex = newCommittedId
        print 'NEW COMMITED INDEX: %s' % self.commitIndex
        assert self.commitIndex <= self.log.getLastLogIndex()
        self.stateChanged.notifyAll()

        if self.state == LEADER and self.commitIndex >= self.configuration.id:
            if not configuration.hasVote(configuration.localServer):
                self.stepDown(self.currentTerm + 1)
                return
        if self.configuration.state == TRANSITIONAL:
            entry = Entry()
            entry.term = self.currentTerm
            entry.type = CONFIGURATION
            entry.configuration.prev_configuration.CopyFrom(self.configuration.description.next_configuration)
            self.append(entry)

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
        print 'appendEntries'.center(80, '#')
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
        request.opcode = APPEND_ENTRIES
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
                request.entries.extend([entry])
                entryId += 1
                numEntries += 1

        request.commit_index = min(self.commitIndex, prevLogIndex + numEntries)
        epoch = self.currentEpoch
        start = datetime.datetime.now()

        message = peer.callRPC(request)
        response = AppendEntries.Response()
        response.ParseFromString(message)        

        if response.term > self.currentTerm:
            self.stepDown(response.term)
        else:
            assert response.term == self.currentTerm
            peer.lastAckEpoch = epoch
            self.stateChanged.notifyAll()
            peer.nextHeartbeatTime = start + datetime.timedelta(seconds = HEARTBEAT_PERIOD_SECONDS)
            
            if response.success:
                print 'lastAgreeIndex', peer.lastAgreeIndex, prevLogIndex, numEntries
                if peer.lastAgreeIndex > prevLogIndex + numEntries:
                    pass
                else:
                    peer.lastAgreeIndex = prevLogIndex + numEntries
                    print 'lastAgreeIndex = %s' % peer.lastAgreeIndex
                    self.advanceCommittedId()

                peer.nextIndex = peer.lastAgreeIndex + 1
                peer.forceHeartbeat = False
                
                if not peer.isCaughtUp_ and peer.thisCatchUpIterationGoalId <= peer.lastAgreeIndex:
                    duration = (datetime.datetime.now() - peer.thisCatchUpIterationStart).seconds
                    thisCatchUpIterationMs = duration * 1000
                    if (peer.lastCatchUpIterationMs - thisCatchUpIterationMs) < ELECTION_TIMEOUT_SECONDS:
                        peer.isCaughtUp_ = True
                        self.stateChanged.notifyAll()
                    else:
                        peer.lastCatchUpIterationMs = thisCatchUpIterationMs
                        peer.thisCatchUpIterationStart = datetime.datetime.now()
                        peer.thisCatchUpIterationGoalId = self.log.getLastLogIndex()
                    pass
            else:
                if peer.nextIndex > 1:
                    peer.nextIndex -= 1

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
        lastLogIndex = self.log.getLastLogIndex()
        if lastLogIndex >= self.log.getLogStartIndex():
            return self.log.getEntry(lastLogIndex).term
        else:
            assert lastLogIndex == self.lastSnapshotIndex
            return lastSnapshotTerm
        pass

    def interruptAll(self):
        pass

    def readSnapshot(self):
        pass

    def replicateEntry(self, entry):
        if self.state == LEADER:
            entry.term = self.currentTerm
            self.append(entry)
            index = self.log.getLastLogIndex()
            while not self.exiting and self.currentTerm == entry.term:
                if self.commitIndex >= index:
                    print 'replicate succeeded!'
                    return True
                print self.commitIndex, index
                self.stateChanged.wait()
        return False

    def requestVote(self, peer):
        print 'REQUEST VOTE'
        request = RequestVote.Request()
        request.opcode = REQUEST_VOTE
        request.server_id = self.serverId
        request.recipient_id = peer.serverId
        request.term = self.currentTerm
        request.last_log_term = self.getLastLogTerm()
        request.last_log_index = self.log.getLastLogIndex()
        
        start = datetime.datetime.now()
        epoch = self.currentEpoch
        message = peer.callRPC(request)
        response = RequestVote.Response()
        response.ParseFromString(message)
        
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
        self.stateChanged.notifyAll()
        pass

    def startNewElection(self):
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
