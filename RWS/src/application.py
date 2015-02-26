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
import os
import random
import subprocess
import sys
import cherrypy

from src.auth import authRequestHandler

sys.path.append(os.getcwd() + "/../SPMC")
from hadoop import hadoop
from user import User

class Application(object):
    exposed=True

    @authRequestHandler
    def GET(self, arg):
        return {'applications': self.list()}

    def list(self):
        applications = []
        for app in hadoop.list():
            application = app.to_dict()
            applications.append(application)

        return applications

    def create(self, app_name, app_type):
        hadoop.create({
                        'user': 'administrator',
                        'name': app_name
                      })

    def opr(self, app, op):
        f = getattr(hadoop, op)
        f({'application_id': app})
    
    @cherrypy.tools.json_in()
    @authRequestHandler
    def POST(self, op):
        data = cherrypy.request.json
        if op == 'create':
            app_type = data.get('app_type')
            app_name = data.get('app_name')
            self.create(app_name, app_type)
            return {
                    'msg': 'Application %s successfully %sd' % (app_name, op),
                    'applications': [{
                                'cluster_id' : 'clust_%s' %  random.randint(0, 1000),
                                'name': app_name,
                                'created': '10 Jan 2015 22:10:13',
                                'modified': '4 Feb 2015 14:11:13',
                                'vipnetwork': '10.10.10.109',
                                'owner': 'sumit',
                                'astate': self.app_status[op],
                                'type': app_type,
                               }
                              ]
            }

        applications = []
        apps = data.get('apps')
        for app in apps:
            self.opr(app, op)
            applications.append(
                                {
                                  'cluster_id': app,
                                  'name': 'log_analyzer',
                                  'modified': '4 Feb 2015 14:30:19', 
                                  'astate': self.app_status[op]
                                 }
                               )
        return {
                'msg': 'Applications successfully updated',
                'applications': self.list()
               }

conf = {
         '/': {
             'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
             'tools.sessions.on': True,
             'tools.response_headers.on': True
         }
      }

app = cherrypy.Application(Application(), '/application', config = conf)
