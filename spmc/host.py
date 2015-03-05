import datetime
import getopt
import sqlalchemy

from configdb import *
from configuration import *
from ports import *

class Host(object):
    @classmethod
    def create(cls, name, ipaddress):
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
            host = DBPhysicalHost(
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

    @classmethod
    def update(cls, name, old_ipaddress, new_ipaddress):
        # Check if IP already exists
        query = session.query(DBPhysicalHost)
        if query.filter(DBPhysicalHost.ipaddress == old_ipaddress).count() == 0:
            #Old IP address does not exist, create a new host here.
            host = cls.create(name, new_ipaddress)
        else:
            #Update the existing one.
            host = query.filter(DBPhysicalHost.ipaddress == old_ipaddress).one()
            host.name = name
            host.ipaddress = new_ipaddress
        session.add(host)
        session.flush()

    @classmethod
    def delete(cls, ipaddress):
        query = session.query(DBPhysicalHost)
        host = query.filter(DBPhysicalHost.ipaddress == ipaddress).one()
        if len(host.virtualhosts) != 0:
            raise Exception("Host cannot be removed. %s virtual nodes exist." %
                            len(host.virtualhosts))

        session.delete(host)
        session.commit()

    @classmethod
    def listing(cls):
        return session.query(DBPhysicalHost)

def usage():
    print ("usage: host.py --create --name=hostname --ipaddress=ipaddress")
    print ("usage: host.py --delete --ipaddress=ipaddress")
    print ("usage: host.py --list")
    sys.exit(1)

def main():
    ops = []
    create = False
    delete = False
    listing = False
    name = None
    ipaddress = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "", 
                                   ["create",
                                    "delete",
                                    "help",
                                    "list",
                                    "name=",
                                    "ipaddress="
                                    ])

    except (getopt.GetoptError, err):
        print (str(err))
        usage()
        sys.exit(2)
    for o, a in opts:
        if o in ("--create"):
            ops.append(a)
            create = True
        elif o in ("--delete"):
            ops.append(a)
            delete = True
        elif o in ("--list"):
            ops.append(a)
            listing = True
        elif o in ("--name"):
            name = a
        elif o in ("--ipaddress"):
            ipaddress = a
        elif o in ("--help"):
            usage()

    if len(ops) > 1:
        usage()
    
    if create:
        if not name or not ipaddress:
            usage()

        Host.create(name, ipaddress)

    elif delete:
        if not ipaddress:
            usage()

        Host.delete(ipaddress)

    elif listing:
        # make sure this is the last clause we handle in the if switch
        hosts = Host.listing()
        if hosts.count() > 0:
            print ("{:<16s}{:<16s}{:<16s}{:<32s}".format("host name", "ipaddress", "app nodes", "created"))
        for host in hosts:
            print ("{:<16s}{:<16s}{:<16d}{:<32s}".format(
                    host.name, host.ipaddress, len(host.virtualhosts), str(host.created))
                   )
    else:
        usage()

if __name__ == '__main__':
    try:
        main()
    except:
        print(sys.exc_info()[1])
