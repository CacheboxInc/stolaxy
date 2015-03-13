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
import cherrypy
from src.auth import role, roles
from src.util import check_password

from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('./templates'))

sys.path.append(os.getcwd() + "/../spmc")
from user import User

class Login(object):
    exposed = True

    def GET(self):
        if 'logged_in' not in cherrypy.session:
            template = env.get_template('login.html')
            return template.render(login_action = "/login")
        template = env.get_template('home.html')
        return template.render(session = cherrypy.session, roles=roles)

    def POST(self, *args, **kwargs):
        data = cherrypy.request.params
        email = data.get('login')
        password = data.get('password')
        template = env.get_template('home.html')
        login_error = True
        user = User.get_by_email(email)
        if user:
            #Check if password is valid or not
            if check_password(password, user.password):
                cherrypy.session['userid'] = user.id
                cherrypy.session['username'] = user.username
                cherrypy.session['email'] = user.email
                cherrypy.session['logged_in'] = True
                cherrypy.session['role'] = user.role
                User.record_login(user.id)
                login_error = False
            else:
                template = env.get_template('login.html')
        else:
            template = env.get_template('login.html')

        return template.render(session = cherrypy.session, roles = roles, \
                                 login_error = login_error)

     
class Logout(object):
    exposed = True

    def GET(self):
        userid =  cherrypy.session.get('userid', None)
        if userid is not None:
            User.record_logout(userid)
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
