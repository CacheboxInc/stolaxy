#!/usr/bin/env python3

from configdb import DBGroup

class Group(object):
    def __init__(self, name):
        configuration = session.query(DBGroup).one()
