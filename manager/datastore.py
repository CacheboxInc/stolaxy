#!/usr/bin/env python3

import datetime
import sqlalchemy

from configdb import *

DEFAULT_DATASTORE_SIZE = 100 << 30 # 100 GB

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
        dtype = kwargs.get('dtype', 'VOLUME')
        
        datastore = DBDatastore(
            application_id = application_id,
            created = now,
            modified = now,
            name = name.strip().lower(),
            path = path,
            dtype = dtype,
            )

        session.add(datastore)
        session.commit()

        return datastore

if __name__ == '__main__':
    datastore1 = Datastore.create('test_ds1')
