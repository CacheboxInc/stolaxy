#!/usr/bin/env python

#
# Copyright 2014 Cachebox, Inc. All rights reserved. This software
# is property of Cachebox, Inc and contains trade secrects,
# confidential & proprietary information. Use, disclosure or copying
# this without explicit written permission from Cachebox, Inc is
# prohibited.
#
# Author: Cachebox, Inc (sales@cachebox.com)
#

import os
import sys
import json
import random
import subprocess
import cherrypy

from src.auth import authRequestHandler, authAdminRequestHandler

sys.path.append(os.getcwd()+"/../spmc")
from group import Group

class Groups(object):
    exposed = True

    groups = [{
               'id': random.randint(0, 100),
               'created': '19 Jan 2015 12:01:09',
               'modified': '20 Jan 2015 23:11:10',
               'name': 'System Admins',
               'users': ",".join(['user1', 'user2']),
               'user_ids': ",".join(['1', '2'])
             }]

    @authAdminRequestHandler
    def GET(self, arg):
        groups = []
        for g in Group.listing():
            groups.append(g.to_dict())
        return {'groups': groups}

    def create(self, **args):
        return Group.create_or_get(**args)

    def update(self, **args):
        return Group.update(**args)

    def delete(self, group_id):
        return Group.delete(group_id)

    @cherrypy.tools.json_in()
    @authAdminRequestHandler
    def POST(self, op):
        data = cherrypy.request.json
        error = False
        group = False

        if op == 'create':
            '''
            Create script for group
            '''
            if not Group.get_by_name(data.get('name', None)):
                group = self.create(**data)
                group = group.to_dict()
                msg = "Group %s successfully created" % group.get('name', None)
            else:
                error = True
                msg = "Group %s already exists" % data.get('name', None)
        elif op == 'update':
            '''
            Update script for group
            '''
            id = data.get('id', None)
            name = data.get('name', None)
            if not Group.group_exists(id=id, name=name):
                group = self.update(**data)
                group = group.to_dict()
                msg = "Group %s successfully updated" % group.get('name', None)
            else:
                error = True
                msg = "Group %s already exists" % data.get('name', None)
        elif op == 'delete':
            '''
            Delete script for group
            '''
            id = data.get('id', None)
            self.delete(id)
            msg = "Group successfully deleted" 

        return {
                'msg': msg,
                'error': error,
                'groups': [group]
        }
 
    
conf = {
         '/': {
             'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
             'tools.sessions.on': True,
             'tools.response_headers.on': True
         }
      }

app = cherrypy.Application(Groups(), '/group', config = conf)
