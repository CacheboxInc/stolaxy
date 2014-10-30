# A Simple UDP class

import socket

class UDP(object):
    """simple UDP ping class"""
    handle = None   # Socket for send/recv
    port = 0        # UDP port we work on
    address = ''    # Own address
    broadcast = ''  # Broadcast address

    def __init__(self, port, name, serverId, address=None, broadcast=None):
        if address is None:
            local_addrs = socket.gethostbyname_ex(socket.gethostname())[-1]
            for addr in local_addrs:
                if not addr.startswith('127'):
                    address = addr
        if broadcast is None:
            broadcast = '255.255.255.255'

        self.address = address
        self.broadcast = broadcast
        self.port = port
        self.name = name
        self.serverId = serverId
        # Create UDP socket
        self.handle = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        # Ask operating system to let us do broadcasts from socket
        self.handle.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Bind UDP socket to local port so we can receive pings
        self.handle.bind(('', port))

    def send(self, buf, name):
        data = '%s,%s,%s' % (buf, name, self.serverId)
        self.handle.sendto(data, 0, (self.broadcast, self.port))

    def recv(self, n):
        buf, addrinfo = self.handle.recvfrom(n)
        uid = buf.split(',')[0]
        name = buf.split(',')[1]
        serverId = buf.split(',')[2]
        return (uid, name, serverId, addrinfo[0], addrinfo[1])
