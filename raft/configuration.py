from server import *

class SimpleConfiguration(object):
    def __init__(self):
        self.servers = []

    def all(self, predicate):
        for server in self.servers:
            if not getattr(server, predicate)():
                return False

        return True

    def contains(self, s):
        for server in self.servers:
            if server.serverId == s.serverId:
                return True

        return False

    def forEach(self, sideEffect):
        for server in self.servers.values():
            getattr(server, sideEffect)()

    def min(self, getValue):
        if len(self.servers) == 0:
            return 0

        smallest = 0
        for server in self.servers:
            smallest = min(smallest, getattr(server, getValue)())

        return smallest

    def quorumAll(self, predicate):
        if len(self.servers) == 0:
            return True

        count = 0
        for server in self.servers:
            if getattr(server, predicate)():
                count += 1
        
        return count >= len(self.servers) / 2 + 1

    def quorumMin(self, getValue):
        if len(self.servers) == 0:
            return 0

        values = []
        for server in self.servers:
            values.push(getattr(server, getValue)())
            
        values.sort()
        return values[(len(values) - 1)/2]

    
class Configuration(object):
    def __init__(self, serverId, consensus):
        self.consensus = consensus
        self.localServer = LocalServer(serverId, consensus)
        self.knownServers = {serverId:self.localServer}
        self.oldServers = SimpleConfiguration()
        self.newServers = SimpleConfiguration()
        self.state = BLANK
        self.id = 0
        self.description = None

    def forEach(self, sideEffect):
        for server in self.knownServers.values():
            getattr(server, sideEffect)()

    def hasVote(self, server):
        if self.state == TRANSITIONAL:
            return self.oldServers.has_key(server) or self.newServers.has_key(server)
        else:
            return oldeServers.has_key(server)

    def lookupAddress(self, serverId):
        for server in self.knownServers.values():
            if server.serverId == serverId:
                return server.address

        return None

    def quorumAll(self, predicate):
        if self.state == TRANSITIONAL:
            return self.oldServers.quorumAll(predicate) and newServers.quorumAll(predicate)
        else:
            return self.oldServers.quorumAll(predicate)

    def quorumMin(self, getValue):
        if self.state == TRANSITIONAL:
            return min(self.oldServers.quorumMin(getValue), self.newServers.quorumMin(getValue))
        else:
            return self.oldServers.quorumMin(getValue)

    def reset(self):
        self.state = BLANK
        self.id = 0
        self.description = None
        self.oldServers.servers = {}
        self.newServers.servers = {}
        self.knownServers = {}
        self.knownServers[self.localServer.serverId] = self.localServer

    def setStagingServers(self, stagingServers):
        assert self.state == STABLE
        self.state = STAGING
        for address, port, serverId in stagingServers:
            server = self.getServer(serverId)
            server.address = address
            self.newServers.servers.append(server)

    def resetStagingServers(self):
        if self.state == STAGING:
            self.setConfiguration(self.id, self.description)

    def setConfiguration(self, newId, newDescription):
        if len(newDescription.next_configuration.servers) == 0:
            self.state = STABLE
        else:
            self.state = TRANSITIONAL

        self.id = newId
        self.description= newDescription
        self.oldServers.servers = []
        self.newServers.servers = []
        
        for s in self.description.prev_configuration.servers:
            server = self.getServer(s.id)
            server.address = s.address
            self.oldServers.servers.append(server)

        for s in self.description.next_configuration.servers:
            server = self.getServer(s.id)
            server.address = s.address
            self.oldServers.servers.append(server)

        print 'setConfiguration.TBD. state = %s' % self.state

    def stagingAll(self, predicate):
        if self.state == STAGING:
            return self.newServers.all(predicate)
        
        return True

    def stagingMin(self, getValue):
        if self.state == STAGING:
            return self.newServers.min(getValue)

        return 0

    def getServer(self, newServerId):
        if self.knownServers.has_key(newServerId):
            return self.knownServers[newServerId]

        peer = Peer(newServerId, self.consensus)
        peer.startThread()
        self.knownServers[newServerId] = peer
        return peer


class ConfigurationManager(object):
    def __init__(self, configuration):
        self.configuration = configuration
        self.descriptions = {}

    def add(self, index, description):
        self.descriptions[index] = description
        self.restoreInvariants()
        pass

    def restoreInvariants(self):
        if len(self.descriptions) == 0:
            self.configuration.reset()
        else:
            for configid in self.descriptions:
                if self.configuration.id != configid:
                    self.configuration.setConfiguration(configid, self.descriptions[configid])
