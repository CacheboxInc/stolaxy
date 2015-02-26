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

import cherrypy
from src.auth import role

from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('./templates'))

class Login(object):
    exposed = True

    def GET(self):
        if 'logged_in' not in cherrypy.session:
            template = env.get_template('login.html')
            return template.render(login_action = "/login")
        template = env.get_template('home.html')
        return template.render(session = cherrypy.session)

    def POST(self, *args, **kwargs):
        data = cherrypy.request.params
        username = data.get('login')
        password = data.get('password')
        cherrypy.session['username'] = username
        cherrypy.session['logged_in'] = True
        cherrypy.session['role'] = role.get(username.lower(), 'user')
        template = env.get_template('home.html')
        return template.render(session = cherrypy.session)

class Logout(object):
    exposed = True

    def GET(self):
        cherrypy.lib.sessions.expire()
        template = env.get_template('login.html')
        return template.render(login_action = "/login")

conf = {
         '/': {
             'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
             'tools.sessions.on': True,
             'tools.response_headers.on': True
         },
         '/login': {
             'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
             'tools.sessions.on': True,
             'tools.response_headers.on': True
         },
         '/logout': {
             'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
             'tools.sessions.on': True,
             'tools.response_headers.on': True
         }
      }

webapp = Login()
webapp.login = Login()
webapp.logout = Logout()

app = cherrypy.Application(webapp, '/', config = conf)
