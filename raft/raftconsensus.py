import datetime
import logging
import random
import threading
import time
import zlib
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

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('raft')
logger.setLevel(logging.INFO)

class RaftConsensus(Consensus):
    def __init__(self, serverId, serverAddress):
        Consensus.__init__(self, serverId, serverAddress)
        self.mutex = threading.Lock()
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
        self.message_number = 0
        self.zctx = zmq.Context()
        t = threading.Thread(target = self.rpcHandlerThread)
        t.start()

    def replicate(self, blob, blocking = False, timeout = 0):
        """
        replicate the blob to peers. if blocking is true, the blob is
        guaranteed to be applied to peer logs before the call returns,
        except when combined with timeout. returns True when the logs
        are successfully replicated. timeout is specified in
        seconds. if nonzero then the replicate call returns in
        approximately timeout seconds. Note: return value of false is
        not a guarantee that the operation failed. the caller should
        ensure that the operation is idempotent before issuing a
        retry.
        """
        assert self.state == LEADER

        ret = True
        entry = Entry()
        entry.type = DATA
        entry.data = blob
        self.mutex.acquire()
        entry.term = self.currentTerm
        self.append(entry)

        if blocking:
            ret = False
            if timeout != 0:
                start = datetime.datetime.now()
            index = self.log.getLastLogIndex()
            while not self.exiting and self.currentTerm == entry.term:
                if self.commitIndex >= index:
                    ret = True
                    break

                if timeout != 0:
                    self.stateChanged.wait(timeout)
                else:
                    self.stateChanged.wait()
        
                if (datetime.datetime.now() - start).seconds >= timeout:
                    break

        self.mutex.release()
        return ret

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
        assert self.currentTerm == 0 and self.log.getLogStartIndex() == 1 and \
            self.log.getLastLogIndex() == 0 and self.lastSnapshotIndex == 0

        self.stepDown(1)
        entry = Entry()
        entry.term = 1
        entry.type = CONFIGURATION
        server = Server()
        server.server_id = self.serverId
        server.address = self.serverAddress

        prev_configuration = SimpleConfiguration()
        prev_configuration.servers.extend([server])
        entry.configuration.prev_configuration.CopyFrom(prev_configuration)
        
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
        response.message_number = request.message_number
        
        if request.term < self.currentTerm:
            self.mutex.release()
            return response

        if request.term > self.currentTerm:
            logger.info('caller %s has newer term, updating from %s to %s' % (
                    request.server_id, self.currentTerm, request.term))
            response.term = request.term
        
        self.stepDown(request.term)
        self.setElectionTimer()
        self.withholdVotesUntil = datetime.datetime.now() + \
            datetime.timedelta(ELECTION_TIMEOUT_SECONDS)
        
        if self.leaderId == 0:
            self.leaderId = request.server_id
        else:
            assert self.leaderId == request.server_id

        if request.prev_log_index > self.log.getLastLogIndex():
            logger.warn('rejecting append entries RPC. would leave a gap')
            self.mutex.release()
            return response

        if request.prev_log_index >= self.log.getLogStartIndex() and \
                self.log.getEntry(request.prev_log_index).term != request.prev_log_term:
            logger.warn('rejecting append entries RPC. terms dont agree')
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
                if self.log.getEntry(entryId).term == entry.term:
                    continue

                assert self.commitIndex < entryId
                logger.info('Truncating %s entries after %s from the log' % (
                        self.log.getLastLogIndex() - entryId + 1, entryId - 1))

                self.log.truncateSuffix(entryId - 1)
                self.configurationManager.truncateSuffix(entryId - 1)

            entries.append(entry)

        if len(entries) > 0:
            self.append(entries)

        if self.commitIndex < request.commit_index:
            self.commitIndex = request.commit_index
            assert self.commitIndex <= self.log.getLastLogIndex()
            self.stateChanged.notifyAll()

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
        response.granted = request.term == self.currentTerm \
            and self.votedFor == request.server_id
        self.mutex.release()
        pass

    def setConfiguration(self, oldId, members):
        self.mutex.acquire()
        if self.state != LEADER:
            self.mutex.release()
            return False
        
        logger.info('changing raft configuration to: %s' % members)
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
        checkProgressAt = datetime.datetime.now() + \
            datetime.timedelta(seconds = ELECTION_TIMEOUT_SECONDS)

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
                    checkProgressAt = datetime.datetime.now() + \
                        datetime.timedelta(seconds = ELECTION_TIMEOUT_SECONDS)
                    
            self.stateChanged.wait(ELECTION_TIMEOUT_SECONDS)

        newConfiguration = Configuration()
        newConfiguration.prev_configuration.CopyFrom(
            self.configuration.description.prev_configuration)
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
                self.mutex.acquire()
                
                if self.state == LEADER and self.currentTerm == term:
                    self.configuration.localServer.lastSyncedIndex = sync.lastIndex
                    self.advanceCommittedId()

                self.log.syncComplete()

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
                    if not peer.requestVoteDone:
                        self.requestVote(peer)
                    else:
                        waituntil = datetime.datetime.max
                elif self.state == LEADER:
                    if peer.getLastAgreeIndex() < self.log.getLastLogIndex() \
                            or peer.nextHeartbeatTime < now:
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
        handler = self.zctx.socket(zmq.REP)
        handler.bind('tcp://%s:5556' % self.serverAddress)
        while True:
            message = handler.recv()
            
            rpc = RPC()
            rpc.ParseFromString(message)
            response = None

            if rpc.opcode == APPEND_ENTRIES:
                ae = AppendEntries.Request()
                ae.ParseFromString(message)
                response = self.handleAppendEntries(ae)
                message_number = response.message_number
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
        if self.commitIndex >= newCommittedId:
            return

        assert newCommittedId >= self.log.getLogStartIndex()
        if self.log.getEntry(newCommittedId).term != self.currentTerm:
            return

        self.commitIndex = newCommittedId
        assert self.commitIndex <= self.log.getLastLogIndex()
        self.stateChanged.notifyAll()

        if self.state == LEADER and self.commitIndex >= self.configuration.id:
            if not self.configuration.hasVote(self.configuration.localServer):
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
            elif entry.type == DATA and self.state is not LEADER:
                self.callback(entry.data)

            index += 1

        self.stateChanged.notifyAll()
        
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
        request.opcode = APPEND_ENTRIES
        request.message_number = self.message_number
        self.message_number += 1
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

        message = peer.callRPC(request, self.mutex)
        response = AppendEntries.Response()
        response.ParseFromString(message)        

        assert request.message_number == response.message_number

        if response.term > self.currentTerm:
            self.stepDown(response.term)
        else:
            assert response.term == self.currentTerm
            peer.lastAckEpoch = epoch
            self.stateChanged.notifyAll()
            peer.nextHeartbeatTime = start + datetime.timedelta(seconds = HEARTBEAT_PERIOD_SECONDS)
            
            if response.success:
                if peer.lastAgreeIndex > prevLogIndex + numEntries:
                    pass
                else:
                    peer.lastAgreeIndex = prevLogIndex + numEntries
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
        logger.info('becoming leader for term: %d' % self.currentTerm)
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
                    return True
                self.stateChanged.wait()
        return False

    def requestVote(self, peer):
        request = RequestVote.Request()
        request.opcode = REQUEST_VOTE
        request.server_id = self.serverId
        request.recipient_id = peer.serverId
        request.term = self.currentTerm
        request.message_number = self.message_number
        self.message_number += 1
        request.last_log_term = self.getLastLogTerm()
        request.last_log_index = self.log.getLastLogIndex()
        
        start = datetime.datetime.now()
        epoch = self.currentEpoch
        logger.info('REQUEST VOTE: %s' % request)
        message = peer.callRPC(request, self.mutex)
        response = RequestVote.Response()
        response.ParseFromString(message)
        
        if not response:
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
                logger.info('got vote for term %d' % self.currentTerm)
                if self.configuration.quorumAll('haveVote'):
                    self.becomeLeader()
            else:
                logger.info('vote not granted')

        pass

    def setElectionTimer(self):
        ms = random.randrange(ELECTION_TIMEOUT, ELECTION_TIMEOUT * 2)
        self.startElectionAt = datetime.datetime.now() + datetime.timedelta(seconds = ms/1000)
        logger.debug('starting election at: %s' % self.startElectionAt)
        self.stateChanged.notifyAll()
        pass

    def startNewElection(self):
        # if self.configuration.id == None:
        #     self.setElectionTimer()
        #     return

        if self.state == FOLLOWER:
            logger.info('running for election in term: %d' % (self.currentTerm + 1))

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
            logger.info('no quorum!'.center(80, '#'))

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
