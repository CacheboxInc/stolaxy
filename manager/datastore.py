#!/usr/bin/env python3

import datetime
import sqlalchemy

from configdb import *

DEFAULT_DATASTORE_SIZE = 100 << 30 # 100 GB

datastore_types = {
    'VOLUME':0,
    'FILESYSTEM':1,
    'NFS':2,
    'CEPH':3,
    'AWS-S3':4
    }

class Datastore(object):
    @classmethod
    def get(cls, id):
        query = session.query(DBDatastore)
        return query.filter(DBDatastore.id == id).one()

    @classmethod
    def create(cls, **kwargs):
        now = datetime.datetime.now()

        application = kwargs.get('application')
        if application is not None:
            application_id = application.id
        else:
            application_id = None

        name = kwargs.get('name')
        path = kwargs.get('path')
        size = kwargs.get('size', DEFAULT_DATASTORE_SIZE)
        datastore_type = kwargs.get('dtype', 'FILESYSTEM')
        dtype = datastore_types.get(datastore_type)

        source_path = kwargs.get('source_path', None)
        assert (datastore_type not in ('FILESYSTEM', ) or source_path is not None,
                "FILESYSTEM datastores require a valid source_path")

        container_path = kwargs.get('container_path', '/data')
        backing_volume = kwargs.get('backing_volume')

        datastore = DBDatastore(
            application_id = application_id,
            created = now,
            modified = now,
            name = name.strip().lower(),
            path = path,
            dtype = dtype,
            size = size,
            source_path = source_path,
            container_path = container_path,
            backing_volume = backing_volume
            )

        session.add(datastore)
        session.commit()

        return datastore

if __name__ == '__main__':
    datastore1 = Datastore.create(
            name = 'test_ds1'
            )
