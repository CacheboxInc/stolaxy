#!/usr/bin/env python3

import datetime
import getopt
import sqlalchemy
import sys

from configdb import *
from dcmd import *
from util import *

DEFAULT_DATASTORE_SIZE = 100 << 30 # 100 GB


class Datastore(object):
    datastore_types = {
        'VOLUME':0,
        'FILESYSTEM':1,
        'NFS':2,
        'CEPH':3,
        'AWS-S3':4
        }

    datastore_types_print = {v: k for k, v in datastore_types.items()}

    datastore_tiers = {
        'hdd':0,
        'flash':1,
        'hybrid':2
        }

    datastore_tiers_print = {v: k for k, v in datastore_tiers.items()}

    
    def get(self, **args):
        id = args.get('datastore_id')
        query = session.query(DBDatastore)
        return query.filter(DBDatastore.id == id).one()

    def create(self, **kwargs):
        now = datetime.datetime.now()

        application = kwargs.get('application_id')
        if application is not None:
            application_id = application.id
        else:
            application_id = None

        name = kwargs.get('name')
        if name is None:
            usage()

        path = kwargs.get('path')
        size = kwargs.get('size', DEFAULT_DATASTORE_SIZE)
        datastore_type = kwargs.get('dtype', 'FILESYSTEM')
        dtype = self.datastore_types.get(datastore_type)
        tier = kwargs.get('tier', 'hdd')
        if tier not in ('flash', 'hdd', 'hybrid'):
            usage()

        tier = self.datastore_tiers.get(tier)

        source_path = kwargs.get('source_path', None)
#        assert(datastore_type not in ('FILESYSTEM', ) or source_path is not None,
#                "FILESYSTEM datastores require a valid source_path")

        container_path = kwargs.get('container_path', '/data')
        backing_volume = kwargs.get('backing_volume')

        datastore = DBDatastore(
            application_id = application_id,
            created = now,
            modified = now,
            name = name.strip().lower(),
            dtype = dtype,
            size = size,
            source_path = source_path,
            tier = tier,
            container_path = container_path,
            backing_volume = backing_volume
            )

        session.add(datastore)
        session.commit()

        if tier == 'flash':
            vgroup = STOLAXY_FLASH_TIER_VOLUME_GROUP
        elif tier == 'hdd':
            vgroup = STOLAXY_HDD_TIER_VOLUME_GROUP
        elif tier == 'hybrid':
            assert 0
        else:
            assert 0

        # point to ponder - do we create the volume now, or defer it. there are several options here.

        lvcmd = (
            "lvcreate",
            "-n",
            name,
            "-l",
            size,
            vgroup
            )

        return datastore

    def delete(self, **args):
        datastore_id = args.get('datastore_id')
        if datastore_id == None:
            usage()

        datastore = self.get(**args)
        session.delete(datastore)
        session.commit()
    
    def list(self, **args):
        query = session.query(DBDatastore)
        datastores = query.all()

        if args.get('op') != 'list':
            return datastores
            
        # user has requested this listing, pretty print

        if len(datastores) > 0:
            print ("{:<8s}{:<16s}{:<16s}{:<16s}{:<16s}{:<16s}{:<16s}{:>16s}".format(
                    "id", "name", "type", "tier", "source_path", "container_path", "backing_volume", "size")
                   )
        for ds in datastores:
            dtype = self.datastore_types_print.get(ds.dtype)
            tier = self.datastore_tiers_print.get(ds.tier)

            print ("{:<8d}{:<16s}{:<16s}{:<16s}{:<16s}{:<16s}{:<16s}{:>16s}".format(
                    ds.id, ds.name, dtype, tier, str(ds.source_path), str(ds.container_path),
                    str(ds.backing_volume), getusize(ds.size))
                   )

def usage():
    print("usage: datastore.py --create --name=datastore name --size=datastore_size [--tier=flash|hdd|hybrid]")
    print("usage: datastore.py --update --datastore=datastore id --size=datastore_size")
    print("usage: datastore.py --delete --datastore=datastore id")
    print("usage: datastore.py --list")
    sys.exit(1)

def main():
    ops = []
    datastore = Datastore()
    try:
        opts, args = getopt.getopt(sys.argv[1:], "", 
                                   ["create",
                                    "delete",
                                    "update",
                                    "list",
                                    "size=",
                                    "name=",
                                    "type=",
                                    "datastore=",
                                    "tier=",
                                    ])
        
    except (getopt.GetoptError, err):
        print (str(err))
        usage()
        sys.exit(2)

    args = {}
    for o, a in opts:
        if o in ('--create', '--update', '--delete', '--list'):
            ops.append(o.strip('--'))
            args['op'] = o.strip('--')
        elif o in ("--name"):
            name = a
            args['name'] = a
        elif o in ("--size"):
            size = a
            args['size'] = a
        elif o in ("--datastore", ):
            args['datastore_id'] = a
        elif o in ("--type", ):
            args['dtype'] = a
        elif o in ("--help"):
            usage()
        elif o in ("--tier"):
            args['tier'] = a

    if len(ops) > 1 or len(ops) == 0:
        usage()

    method = getattr(datastore, args.get('op'))
    method(**args)

if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        pass
    except:
        print(sys.exc_info()[1])

