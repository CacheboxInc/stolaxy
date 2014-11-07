#!/usr/bin/env python

import getopt
import sys
import threading

from daemon import Daemon

sys.path.append('../util/')
sys.path.append('../pynfs/')
sys.path.append('../pynfs/nfs40/lib/')
sys.path.append('../cluster/')
sys.path.append('../raft')

from cluster import Cluster
from raftconsensus import *
from raftcluster import reconfigurations
from storage import *

from nfs40 import *

def usage():
	print 'stolaxy.py --address=<ipaddress> --serverid=<serverid> --name=<clustername>'
	sys.exit(1)

class Stolaxy(Daemon):
    def startnfs(self, raft):
	    server = nfsstartup('', 2049, STOLAXY_BACKEND_XFS_FLASH_TIER, raft)
	    raft.callback = server.callback
	    server.run()
	    try:
		    server.unregister()
	    except:
		    pass

    def run(self):
	    storage = Storage()
	    if not storage.initialize():
		    print 'aborting ...'
		    return

	    name = self.name
	    serverid = self.serverid
	    address = self.address

	    cluster = Cluster(name, serverid)
	    raft = RaftConsensus(serverid, address)
	    reconfig = threading.Thread(
		    target = reconfigurations,
		    kwargs = {'raft':raft, 'cluster':cluster}
		    )
	    reconfig.start()

	    nfs = threading.Thread(
		    target = self.startnfs,
		    kwargs = {'raft':raft}
		    )
	    nfs.start()
	    
	    nfs.join()
	    reconfig.join()
	    
def main():
    	serverId = None
	address = None
	foreground = True
	name = None

	try:
		opts, args = getopt.getopt(sys.argv[1:], "", [
				"foreground",
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
		elif o in ("--foreground"):
			foreground = True
		elif o in ("--address="):
			address = a 
		elif o in ("--serverid"):
			serverId = int(a)

	if name is None or address is None or serverId is None:
		usage()

	stolaxy = Stolaxy('/tmp/stolaxy.pid', chdir='/tmp')
	stolaxy.name = name
	stolaxy.address = address
	stolaxy.serverid = serverId

	if foreground:
		stolaxy.run()


if __name__ =='__main__':
	main()
