"""UDP ping command
Model 3, uses abstract network interface
"""

import getopt
import random
import sys

from cluster import Cluster

def usage():
    print 'usage: discovery.py [--name=cluster_name]'

def main(name):
    print 'forming cluster with name: %s' % name
    cluster = Cluster(name)
    while True:
        try:
            print(cluster.recv())
        except KeyboardInterrupt:
            print("interrupted")
            break
    cluster.stop()

if __name__ == '__main__':

    name = 'cluster%d' % random.randrange(0, 100000)

    try:
        opts, args = getopt.getopt(sys.argv[1:], "", 
                                   ["name=", 
                                    ])

    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)
    for o, a in opts:
        if o in ("--name"):
            name = a
    
    main(name)
