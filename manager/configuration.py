import datetime

from configdb import DBConfiguration, DBGroup
from configdb import session
from netaddr import *
from sqlalchemy.orm.exc import NoResultFound

MAX_NETWORKS = 1 << 24
MAX_NETWORKS_BYTEARRAY_LEN = MAX_NETWORKS >> 3

VIRTUAL_IP_NETWORK_START = '10.0.0.0/24'

class Configuration(object):
    def __init__(self):
        try:
            configuration = session.query(DBConfiguration).one()
        except NoResultFound:
            configuration = DBConfiguration(
                vipaddresses = bytearray(MAX_NETWORKS_BYTEARRAY_LEN),
                vipallocate = VIRTUAL_IP_NETWORK_START
                )
            
            now = datetime.datetime.now()
            defaultgroup = DBGroup(
                created = now,
                modified = now,
                name = 'default'
                )

            session.add(configuration)
            session.add(defaultgroup)

            session.commit()

        self.configuration = configuration
        
    def assignVIPNetwork(self):
        configuration = self.configuration

        network = IPNetwork(configuration.vipallocate)
        vipnetwork = network
        network += 1
        
        configuration.vipallocate = str(network)
        return vipnetwork

configuration = Configuration()
