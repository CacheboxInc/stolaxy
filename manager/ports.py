#!/usr/bin/env python3

MAX_PORTS = 1 << 17 # let us support 128K ports

# the minimum port number we can assign. should be a power of 2

MIN_START_PORT = 1 << 13 

MIN_PORT_BYTEARRAY_INDEX  = MIN_START_PORT >> 3
MAX_PORTS_BYTEARRAY_LEN = MAX_PORTS >> 3

class Ports(object):
    def __init__(self, ports):
        assert len(ports) == MAX_PORTS_BYTEARRAY_LEN
        self.ports = bytearray(ports)

    def assignFreePort(self, numports = 1, scanstart = MIN_START_PORT):
        """returns numports number of ports as a list. """
        
        if scanstart < MIN_START_PORT:
            scanstart = MIN_START_PORT

        ssindex = scanstart >> 3

        for index in range(ssindex, MAX_PORTS_BYTEARRAY_LEN):
            assert(index >= 0 and index < MAX_PORTS_BYTEARRAY_LEN)
            portbyte = self.ports[index]
            assert portbyte >= 0 and portbyte <= 255
            if portbyte == 255:
                continue

            bit = 0
            for bit in range(0, 8):
                if portbyte & (1 << bit):
                    continue
                break
            
            port = (index << 3) + bit
#            print ('bit', bit, 'in byte', index, 'is available', 'port #', port, bin(portbyte))
            self.ports[index] |= (1 << bit)
            return port

        return None

    @classmethod
    def initPorts(cls):
        """ initializes a backend ports bitmap for use """
        return bytearray(MAX_PORTS_BYTEARRAY_LEN)

if __name__ == '__main__':
    ports = Ports.initPorts()
    ports = Ports(ports)
    for i in range(0, 10):
        print(ports.assignFreePort())
