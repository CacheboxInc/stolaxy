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
        return {'groups': self.groups}

    @cherrypy.tools.json_in()
    @authAdminRequestHandler
    def POST(self, op):
        data = cherrypy.request.json
        group_id = data.get('group_id', random.randint(0, 100))
        users = data.get('group_users')
        name = data.get('group_name')
        return {
                'msg': "Group %s successfully created" % name,
                'groups':[
                {
                  'id': group_id,
                  'created': '19 Jan 2015 12:01:09',
                  'modified': '20 Jan 2015 23:11:10',
                  'name': name,
                  'users': ",".join(['user1', 'user2']),
                  'user_ids': ",".join(users)
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

app = cherrypy.Application(Groups(), '/group', config = conf)
