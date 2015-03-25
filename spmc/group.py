#!/usr/bin/env python3

import datetime
import sqlalchemy

from configdb import *
import user

class Group(object):
    def __init__(self, name):
        query = session.query(DBGroup)
        group = query.filter(DBGroup.name == name).one()
        self.group = group

    @classmethod
    def get_by_id(self, id):
        try:
            query = session.query(DBGroup)
            group = query.filter(DBGroup.id == id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            group = False
        return group

    @classmethod
    def get_by_name(self, name):
        try:
            query = session.query(DBGroup)
            group = query.filter(DBGroup.name == name).one()
        except sqlalchemy.orm.exc.NoResultFound:
            group = False
        return group

    @classmethod
    def group_exists(self, **args):
        id = args.get('id', None)
        name = args.get('name', None)
        try:
            query = session.query(DBGroup)
            group = query.filter(
                            sqlalchemy.and_(
                              DBGroup.name == name, DBGroup.id!=id)
                            ).one()
        except sqlalchemy.orm.exc.NoResultFound:
            group = False
        return group

    @classmethod
    def create_or_get(cls, **args):
        try:
            query = session.query(DBGroup)
            return query.filter(DBGroup.name == args.get('name', None)).one()
        except sqlalchemy.orm.exc.NoResultFound:
            now = datetime.datetime.now()
            group = DBGroup(
                created = now,
                modified = now,
                name = args.get('name').strip().lower(),
                )
            users = args.get('users', None)
            for u in users:
                usr = user.User.get_by_id(u)
                if usr:
                    group.users.append(usr)
            
            session.add(group)
            session.commit()
            return group

    @classmethod
    def delete(cls, group_id):
        try:
            group = cls.get_by_id(group_id)
        except sqlalchemy.orm.exc.NoResultFound:
            raise Exception('No group with given ID exists.')
        session.delete(group)
        session.commit()

    @classmethod
    def update(cls, **args):
        try:
            group = cls.get_by_id(args.get('id', None))
        except sqlalchemy.orm.exc.NoResultFound:
            raise Exception("No group with given info exists.")
        now = datetime.datetime.now()
        group.modified = now
        group.name = args.get('name', group.name)
        users = args.get('users', None)
        group.users = []
        for u in users:
            usr = user.User.get_by_id(u)
            if usr:
                group.users.append(usr)

        session.add(group)
        session.commit()
        return group

    @classmethod
    def listing(cls):
        return session.query(DBGroup)

if __name__ == '__main__':
    group1 = Group.create_or_get('test_group1')
    group2 = Group.create_or_get('test_group2')
