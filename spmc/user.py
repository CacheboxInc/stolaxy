#!/usr/bin/env python3

import datetime
import sqlalchemy

from configdb import *
from group import *
from util import generate_password

class User(object):
    @classmethod
    def get(cls, username):
        try:
            query = session.query(DBUser)
            user =  query.filter(DBUser.username == username).one()
        except sqlalchemy.orm.exc.NoResultFound:
            user = False
        return user
    
    @classmethod
    def get_by_id(cls, id):
        try:
            query = session.query(DBUser)
            user = query.filter(DBUser.id == id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            user = False
        return user

    @classmethod
    def get_by_email(cls, email):
        try:
            query = session.query(DBUser)
            user = query.filter(DBUser.email == email).one()
        except sqlalchemy.orm.exc.NoResultFound:
            user = False
        return user

    @classmethod
    def create_or_get(cls, **args):
        try:
            query = session.query(DBUser)
            return query.filter(DBUser.username == args.get('username', None)).one()
        except sqlalchemy.orm.exc.NoResultFound:
            now = datetime.datetime.now()
            #Generate new password for user here
            pwd = args.get('password', generate_password(None))

            user = DBUser(
                role     = args.get('role', None),
                email    = args.get('email', None),
                created  = now,
                modified = now,
                username = args.get('username', None).strip().lower(),
                password = pwd,
                fullname = args.get('fullname', None),
                group_id = args.get('group', None)
                )

            session.add(user)
            session.commit()
            return user

    @classmethod
    def delete(cls, user_id):
        try:
            user = cls.get_by_id(user_id)
        except sqlalchemy.orm.exc.NoResultFound:
            raise Exception('No user with given ID exists.')
        session.delete(user)
        session.commit()

    @classmethod
    def update(cls, **args):
        try:
            user = cls.get_by_id(args.get('id', None))
        except sqlalchemy.orm.exc.NoResultFound:
            raise Exception("No user with given info exists.")
        user.role = args.get('role', user.role)
        user.email = args.get('email', user.email)
        user.username = args.get('username', user.username)
        user.fullname = args.get('fullname', user.fullname)
        user.group_id = args.get('group', user.group)

        session.add(user)
        session.commit()
        return user

    @classmethod
    def record_login(cls, userid):
        try:
            user = cls.get_by_id(userid)
        except sqlalchemy.orm.exc.NoResultFound:
            raise Exception("No user with given info exists.")

        now = datetime.datetime.now()
        if user.firstlogin is None:
           user.firstlogin = now
        user.lastlogin = now
        user.login_count = user.login_count + 1
        user.online = 1

        session.add(user)
        session.commit()

    @classmethod
    def record_logout(cls, userid):
        try:
            user = cls.get_by_id(userid)
        except sqlalchemy.orm.exc.NoResultFound:
            raise Exception("No user with given info exists.")

        user.online = 0
        session.add(user)
        session.commit()

    @classmethod
    def change_password(cls, **data):
        '''
        This method can be used to update the user password and
        reset the user's password request history from database.
        '''
        try:
            user = cls.get_by_id(data.get('id', None))
        except sqlalchemy.orm.exc.NoResultFound:
            raise Exception("No user with given info exists.")
        user.password = data.get('password', user.password)
        user.reset_password = 0
        session.add(user)
        session.commit()
        cls.reset_password_request(data.get('id', None))
        return user

    @classmethod
    def reset_password_request(cls, userid):
        '''
        This method will delete user's password request history
        from database.
        '''
        try:
            query = session.query(DBPasswordRequest)
            pr = query.filter(DBPasswordRequest.userid == userid).one()
        except sqlalchemy.orm.exc.NoResultFound:
            pr = False
        if pr:
            session.delete(pr)
            session.commit()

    @classmethod
    def get_password_request_by_sha(cls, sha):
        try:
            query = session.query(DBPasswordRequest)
            pr = query.filter(DBPasswordRequest.reset_sha == sha).one()
        except sqlalchemy.orm.exc.NoResultFound:
            pr = False 
        return pr

    @classmethod
    def create_or_get_password_request(cls, **data):
        try:
            query = session.query(DBPasswordRequest)
            pr = query.filter(DBPasswordRequest.userid == data.get('id', None)).one()
            pr.reset_sha = data.get('sha')
        except sqlalchemy.orm.exc.NoResultFound:
            now = datetime.datetime.now()
            pr = DBPasswordRequest(
                created = now,
                userid = data.get('id'),
                reset_sha = data.get('sha')
            )
        session.add(pr)
        session.commit()
        return pr

    @classmethod
    def listing(cls):
        return session.query(DBUser).filter(DBUser.role != 'admin')

    @classmethod
    def nongrouplisting(cls, id=None):
        '''
        id: optional param
        if id is given, check for all users having
        userid equals to given id or None.
        '''
        if id is not None:
            return session.query(DBUser).filter(
                       sqlalchemy.and_(
                         sqlalchemy.or_(DBUser.group_id == None, DBUser.group_id == id), 
                         DBUser.role !='admin'
                       )
                   )
        else:
            return session.query(DBUser).filter(
                        sqlalchemy.and_(
                          DBUser.group_id == None, DBUser.role != 'admin')
                        )



if __name__ == '__main__':
    group1 = Group.create_or_get('test_group1')
    user = User.create_or_get('test_user1', group1)
