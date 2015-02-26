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

from src.auth import authAdminRequestHandler
from src.util import getusize

sys.path.append(os.getcwd() + "/../spmc")
from host import Host

class Hosts(object):
    exposed = True

    @authAdminRequestHandler
    def GET(self, arg):
        hosts = []
        for host in Host.listing():
            hosts.append(host.to_dict())
        return {'hosts': hosts}

    def create(self, name, ipaddress):
        Host.create(name, ipaddress)

    def delete(self, ipaddress):
        Host.delete(ipaddress)

    @cherrypy.tools.json_in()
    @authAdminRequestHandler
    def POST(self, op):
        data = cherrypy.request.json
        name = data.get('host_name')
        host_ip = data.get('host_ip')
        old_ip = data.get('host_old_ip', host_ip)
        if op == "create":
            self.create(name, host_ip)
            msg = "Host %s successfully added" % name,
        elif op == 'delete':
            self.delete(host_ip)
            msg = "Host %s successfully removed" % name,
        else:
            msg = "Host %s successfully modified" % name,

        return {
                'msg': msg,
                'hosts':[
                {
                  "name": name,
                  "ipaddress": host_ip,
                  "old_ipaddress": old_ip
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

app = cherrypy.Application(Hosts(), '/host', config = conf)
