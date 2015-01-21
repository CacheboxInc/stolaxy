import datetime
import sqlalchemy

from configdb import PhysicalHost
from configdb import session
from sqlalchemy.util import buffer

def create_host(ipaddress):

    try:
        # validate input

        ipaddress = ipaddress.strip()
        quads = ipaddress.split('.')
        map(lambda x: int(x) >= 0 and int(x) <= 255, quads)

        # verify if the object exists

        now = datetime.datetime.now()
        host = PhysicalHost(ipaddress = ipaddress, created = now, modified = now)
        session.add(host)
        session.commit()
        
    except ValueError:
        print 'malformed IP address: %s' % ipaddress
        return None

    except sqlalchemy.exc.IntegrityError:
        print 'IP address exists: %s' % ipaddress
        return None
    else:
        print 'successfully added host: %s' % ipaddress
        return host

if __name__ == '__main__':
    print create_host('127.0.0.1')
    print create_host('127.0.0.A')
