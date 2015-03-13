import datetime

from configdb import *
from netaddr import *
from sqlalchemy.orm.exc import NoResultFound
from util import *

MAX_NETWORKS = 1 << 24
MAX_NETWORKS_BYTEARRAY_LEN = MAX_NETWORKS >> 3

VIRTUAL_IP_NETWORK_START = '10.0.0.0/24'

ADMIN, USER = 'admin', 'user'
roles = ((ADMIN, "Admininstrator"), (USER, "Regular-User"))

class Configuration(object):
    def __init__(self):
        self.application_types = {
            'MAPREDUCE':0,
            'PIG':1,
            'HIVE':2,
            'HBASE':3,
            'SPARK':4
            }

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
            session.flush()

            pwd = generate_password('admin123')
            defaultuser = DBUser(
                created = now,
                modified = now,
                username = 'administrator',
                password = pwd,
                email = 'admin@cachebox.com',
                role = 'admin',
                group_id = defaultgroup.id
                )

            session.add(defaultuser)
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
