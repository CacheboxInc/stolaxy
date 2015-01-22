import datetime
import sqlalchemy

from configdb import PhysicalHost
from configdb import session
from ports import *

def create_host(ipaddress, name = None):
    """
    creates a database entry for a physical host.
    """

    try:
        ipaddress = ipaddress.strip()
        quads = ipaddress.split('.')
        for x in quads:
            assert (int(x) >= 0 and int(x) <= 255)

        if name == None or len(name) == 0:
            name = 'node-%s%s' % (quads[2], quads[3])

        now = datetime.datetime.now()
        ports = Ports.initPorts()
        host = PhysicalHost(
            ipaddress = ipaddress,
            created = now,
            modified = now,
            ports = ports,
            name = name
            )

        session.add(host)
        session.commit()
        
    except ValueError:
        session.rollback()
        print ('malformed IP address: %s' % ipaddress)
        return None

    except sqlalchemy.exc.IntegrityError:
        session.rollback()
        print ('IP address exists: %s' % ipaddress)
        return None
    else:
        print ('successfully added host: %s' % ipaddress)
        return host

class Host(object):
    @classmethod
    def getHosts(cls, maxhosts = 0):
        """
        return maxhosts physical hosts as a list. if maxhosts is 0,
        return everything in the db.
        """

        return session.query(PhysicalHost).all()

if __name__ == '__main__':
    print (create_host('127.0.0.1'))
    print (create_host('127.0.0.A'))
    hosts = Host.getHosts()
    for host in hosts:
        print (host.ipaddress)
