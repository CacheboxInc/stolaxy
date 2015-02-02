#!/usr/bin/env python3

import datetime
import sqlalchemy

from configdb import *
from group import *

class User(object):
    @classmethod
    def get(cls, name):
        query = session.query(DBUser)
        return query.filter(DBUser.name == name).one()
    
    @classmethod
    def get_by_id(cls, id):
        query = session.query(DBUser)
        return query.filter(DBUser.id == id).one()

    @classmethod
    def create_or_get(cls, name, group):
        try:
            query = session.query(DBUser)
            return query.filter(DBUser.name == name).one()
        except sqlalchemy.orm.exc.NoResultFound:
            now = datetime.datetime.now()

            user = DBUser(
                created = now,
                modified = now,
                name = name.strip().lower(),
                group_id = group.id
                )

            session.add(user)
            session.commit()
            
            return user

if __name__ == '__main__':
    group1 = Group.create_or_get('test_group1')
    user = User.create_or_get('test_user1', group1)
