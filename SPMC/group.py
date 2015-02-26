#!/usr/bin/env python3

import datetime
import sqlalchemy

from configdb import *

class Group(object):
    def __init__(self, name):
        query = session.query(DBGroup)
        group = query.filter(DBGroup.name == name).one()
        self.group = group

    @classmethod
    def create_or_get(cls, name):
        try:
            query = session.query(DBGroup)
            return query.filter(DBGroup.name == name).one()
        except sqlalchemy.orm.exc.NoResultFound:
            now = datetime.datetime.now()
        
            group = DBGroup(
                created = now,
                modified = now,
                name = name.strip().lower(),
                )
            
            session.add(group)
            session.commit()
            return group

if __name__ == '__main__':
    group1 = Group.create_or_get('test_group1')
    group2 = Group.create_or_get('test_group2')
