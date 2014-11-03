"""
This is meant to demonstrate integration of raft and clustering with
automatic detection of node joins and exits which are passed on to
Raft engine.
"""

import getopt
import logging
import random
import socket
import sys
import threading

sys.path.append('../cluster/')

from raftconsensus import *
from cluster import Cluster

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('cluster')
logger.setLevel(logging.INFO)

def usage():
    print 'usage: discovery.py [--name=cluster_name] <--serverid=serverid_numeric> <--address=ipaddress>'

def reconfigurations(raft, cluster):
    while True:
        try:
            what, uid, serverId, address, port = cluster.recv()
            if address == cluster.localAddress() and what == 'JOINED':
                assert cluster.isMember()
                logger.info('%s JOINED the cluster. Starting Raft RSM' % address)
                if len(cluster.members()) == 1:
                    raft.bootstrapConfiguration()
                raft.init(cluster.serverId)
            else:
                assert address != cluster.localAddress()
                if what == 'JOINED':
                    raft.setConfiguration(1, cluster.members())
                
        except KeyboardInterrupt:
            print("interrupted")
            break

if __name__ == '__main__':

    name = 'cluster%d' % random.randrange(0, 100000)
    serverId = None
    address = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "", [
                "address=",
                "name=",
                "serverid=",
                ])

    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)
    for o, a in opts:
        if o in ("--name"):
            name = a
        elif o in ("--address="):
            address = a 
        elif o in ("--serverid"):
            serverId = int(a)
    
    assert address is not None

    logger.info('forming cluster with name: %s, serverId: %s, address: %s' % (name, serverId, address))

    cluster = Cluster(name, serverId)
    raft = RaftConsensus(serverId, address)

    # start a thread to recive notifications on cluster
    # reconfigurations.

    t = threading.Thread(target = reconfigurations, kwargs = {'raft':raft, 'cluster':cluster})
    t.start()

    t.join()
    cluster.stop()
