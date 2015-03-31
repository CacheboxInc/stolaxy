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

from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('./templates'))

sys.path.append(os.getcwd() + "/../spmc")
from user import User

class Profile:
    exposed = True
    def GET(self, arg=None):
        template = env.get_template('profile.html')
        user = User.get_by_id(cherrypy.session.get('userid', None))
        return template.render(session = cherrypy.session, user=user)

conf = {
         '/': {
             'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
             'tools.sessions.on': True,
             'tools.response_headers.on': True
         }
      }

app = cherrypy.Application(Profile(), '/profile', config = conf)
