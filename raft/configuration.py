from server import *

class SimpleConfiguration(object):
    def __init__(self):
        self.servers = []

    def all(self, predicate):
        for server in servers:
            if not predicate(server):
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
        for server in self.servers.values():
            smallest = min(smallest, getValue(server))

        return smallest

    def quorumAll(self, predicate):
        if len(self.servers) == 0:
            return True

        count = 0
        for server in self.servers.values():
            if predicate(server):
                count += 1
        
        return count >= len(self.servers) / 2 + 1

    def quorumMin(self, getValue):
        if len(self.servers) == 0:
            return 0

        values = []
        for server in self.servers.values():
            values.push(getValue(server))
            
        values.sort()
        return values[(len(values) - 1)/2]

    
class Configuration(object):
    def __init__(self, serverId, consensus):
        self.confsensus = consensus
        self.localServer = LocalServer(serverId, consensus)
        self.knownServers = {serverId:self.localServer}
        self.oldServers = SimpleConfiguration()
        self.newServers = SimpleConfiguration()
        self.state = BLANK

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
