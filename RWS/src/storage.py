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
from src.util import getusize

class Storage(object):
    exposed = True

    storages = [
                {
                 'id': random.randint(1, 100),
                 'name': 'HDD Datastore 1',
                 'created': "20 Jan 2015 23:11:10",
                 'modified': "20 Jan 2015 23:11:10",
                 'dtype': "VOLUME",
                 'source_path': "server1",
                 'container_path': "/dev/sdb",
                 'backing_volume': "/dev/sdb,/dev/sdd",
                 'application_id': None,
                 'size' : getusize(4 << 40),
                 'tier': 'hdd',
                 'state': 'created'
                },
                {
                 'id': random.randint(2, 100),
                 'name': 'SSD Datastore 1',
                 'created': "20 Jan 2015 23:11:10",
                 'modified': "20 Jan 2015 23:11:10",
                 'dtype': "VOLUME",
                 'source_path': "server2",
                 'container_path': "/dev/sdb",
                 'backing_volume': "/dev/sdc",
                 'application_id': None,
                 'size' : getusize(1 << 40),
                 'tier': 'flash',
                 'state': 'created'
                },

               ]

    @authRequestHandler
    def GET(self, arg):
        return {'storages': self.storages}

    @cherrypy.tools.json_in()
    @authAdminRequestHandler
    def POST(self, op):
        data = cherrypy.request.json
        storage_id = data.get('storage_id', random.randint(1, 100))
        name = data.get('storage_name')
        volumes = data.get('storage_volumes')
        return {
                'msg': "Datastore %s successfully created" % name,
                'storages':[
                {
                  'id': storage_id,
                  'name': name,
                  'created': "20 Jan 2015 23:11:10",
                  'modified': "20 Jan 2015 23:11:10",
                  'dtype': "VOLUME",
                  'source_path': "server1",
                  'container_path': "/dev/sdb",
                  'backing_volume': "/dev/sdb,/dev/sdd",
                  'application_id': None,
                  'size' : getusize(4 << 40),
                  'tier': 'hdd',
                  'state': 'created'
                }
               ]
        }
 
    
class Volume(object):
    exposed = True

    volumes = [
               {
                 'id': random.randint(1, 100),
                 'name': '/dev/sdb',
                 'type': 'HDD',
                 'size': getusize(2 << 40),
                 'server': 'server1',
                 'datastore': random.randint(1, 100)
               },
               {
                 'id': random.randint(1, 100),
                 'name': '/dev/sdc',
                 'type': 'HDD',
                 'size': getusize(2 << 40),
                 'server': 'server1',
                 'datastore': random.randint(1, 100)
               },
               {
                 'id': random.randint(1, 100),
                 'name': '/dev/sdd',
                 'type': 'SSD',
                 'size': getusize(1 << 40),
                 'server': 'server1',
                 'datastore': None
               },
               {
                 'id': random.randint(1, 100),
                 'name': '/dev/sde',
                 'type': 'HDD',
                 'size': getusize(2 << 40),
                 'server': 'server1',
                 'datastore': None
               },
               {
                 'id': random.randint(1, 100),
                 'name': '/dev/sdb',
                 'type': 'HDD',
                 'size': getusize(2 << 40),
                 'server': 'server2',
                 'datastore': None
               },
               {
                 'id': random.randint(1, 100),
                 'name': '/dev/sdc',
                 'type': 'SSD',
                 'size': getusize(2 << 40),
                 'server': 'server2',
                 'datastore': random.randint(1, 100)
               },
               {
                 'id': random.randint(1, 100),
                 'name': '/dev/sdd',
                 'type': 'SSD',
                 'size': getusize(200 << 30),
                 'server': 'server2',
                 'datastore': None
               }
              ]

    @authAdminRequestHandler
    def GET(self, arg):
        return {'volumes': self.volumes}

conf = {
         '/volume': {
             'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
             'tools.sessions.on': True,
             'tools.response_headers.on': True
         },
         '/': {
             'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
             'tools.sessions.on': True,
             'tools.response_headers.on': True
         }
      }

webapp = Storage()
webapp.volume = Volume()
app = cherrypy.Application(webapp, '/storage', config = conf)
