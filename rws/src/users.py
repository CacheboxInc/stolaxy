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

import json
import random
import subprocess
import cherrypy

from src.auth import authRequestHandler, authAdminRequestHandler

class Users(object):
    exposed = True

    users = [
             {
               'id': random.randint(1, 100),
               'created': '19 Jan 2015 12:01:09',
               'modified': '20 Jan 2015 23:11:10',
               'name': 'user1',
               'group_id': random.randint(1, 100),
               'group': 'group1' 
             },
             {
               'id': random.randint(1, 100),
               'created': '19 Jan 2015 12:01:09',
               'modified': '20 Jan 2015 23:11:10',
               'name': 'user2',
               'group_id': random.randint(1, 100),
               'group': 'group1' 
             },
             {
               'id': random.randint(1, 100),
               'created': '19 Jan 2015 12:01:09',
               'modified': '20 Jan 2015 23:11:10',
               'name': 'user3',
               'group_id': random.randint(1, 100),
               'group': 'group1' 
             },
             {
               'id': random.randint(1, 100),
               'created': '19 Jan 2015 12:01:09',
               'modified': '20 Jan 2015 23:11:10',
               'name': 'user4',
               'group_id': random.randint(1, 100),
               'group': 'group2' 
             },
            ]

    @authAdminRequestHandler
    def GET(self, arg):
        return {'users': self.users}

    @cherrypy.tools.json_in()
    @authAdminRequestHandler
    def POST(self, op):
        data = cherrypy.request.json
        user_id = random.randint(1, 100)
        if op != 'create':
            user_id = data.get("user_id")
        group = data.get("user_group", None)
        name = data.get("user_name")
        return {
                'msg': "User %s successfully created" % name,
                'users':[
                {
                  'id': user_id,
                  'created': '19 Jan 2015 12:01:09',
                  'modified': '20 Jan 2015 23:11:10',
                  'name': name,
                  'group_id': group,
                  'group': 'group1' 
                }
               ]
        }


conf = {
         '/': {
             'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
             'tools.sessions.on': True,
             'tools.response_headers.on': True
         }
      }

app = cherrypy.Application(Users(), '/user', config = conf)
