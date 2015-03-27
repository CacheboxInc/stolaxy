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
from src.util import check_password, generate_password, \
                     forgot_password_sha, send_email

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
        elif cherrypy.session.get('reset_password',0):
            return self.change_password()

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
                cherrypy.session['fullname'] = user.fullname
                cherrypy.session['lastlogin'] = user.lastlogin
                cherrypy.session['email'] = user.email
                cherrypy.session['logged_in'] = True
                cherrypy.session['reset_password'] = user.reset_password
                cherrypy.session['role'] = user.role
                User.record_login(user.id)
                if user.reset_password:
                    return self.change_password()
                login_error = False
            else:
                template = env.get_template('login.html')
        else:
            template = env.get_template('login.html')

        return template.render(session = cherrypy.session, roles = roles, \
                                 login_error = login_error)

    def change_password(self):
        template = env.get_template('change_password.html')
        return template.render(session = cherrypy.session, action = "/reset")
 
class Logout(object):
    exposed = True

    def GET(self):
        userid =  cherrypy.session.get('userid', None)
        if userid is not None:
            User.record_logout(userid)
        cherrypy.lib.sessions.expire()
        template = env.get_template('login.html')
        return template.render(login_action = "/login")

class ResetPassword(object):
    exposed = True

    def GET(self, sha=None):
        reset_request = False
        template = env.get_template('change_password.html')
        msg = ''
        if sha is not None:
            req_user = User.get_password_request_by_sha(sha)
            if req_user:
                cherrypy.session['userid'] = req_user.userid
            else:
                #Reset link is alredy been used.
                template = env.get_template('error.html')
                title = 'Invalid Request'
                msg = 'Oops! It seems like an invalid request. \
                        Either this URL has already been used or expired.'
                return template.render(msg=msg, title=title)
        return template.render(session = cherrypy.session, action = "/reset")

    def POST(self, *args, **kwargs):
        data = cherrypy.request.params
        template = env.get_template('change_password.html')
        success = True
        password1 = data.get('password')
        password2 = data.get('confirm_password')
        if password1 == ''  or password2 == '':
            msg = 'All fields are required.'
            success = False
        elif password1 != password2:
            msg = 'Password doesn\'t match.'
            success = False
        else:
            enc_pwd = generate_password(password1)
            data['password'] = enc_pwd
            user = User.change_password(**data)
            cherrypy.session['reset_password'] = user.reset_password
            raise cherrypy.HTTPRedirect('/login')
        return template.render(session = cherrypy.session, 
                               action = "/reset", success = success, msg = msg)

class ForgotPassword(object):
    exposed = True

    def GET(self):
        template = env.get_template('forgot_password.html')
        return template.render(session = cherrypy.session, action = "/forgot")

    def POST(self, *args, **kwargs):
        data = cherrypy.request.params
        template = env.get_template('forgot_password.html')
        success = True
        email = data.get('email')
        if email == '':
            msg = 'We need this information to find you.'
            success = False
        else:
            user =  User.get_by_email(email)
            if user:
                sha = forgot_password_sha(email, user.id)
                tmpl = env.get_template('forgot-password-content.html')
                tmpl_data = {}
                tmpl_data['link'] = cherrypy.url('.')+'reset?sha='+sha
                tmpl_data['fullname'] = user.fullname
                content = tmpl.render(data=tmpl_data)
                #Record password reset request
                User.create_or_get_password_request(id=user.id, sha=sha)
                try:
                    send_email(content, email)
                except:
                    # We can't send email all the time in development.
                    # Let's skip for now
                    pass

            msg = 'You\'ll receive an email with password \
                     reset link if you\'ve supplied a valid email.'
        return template.render(session = cherrypy.session, 
                               action = "/reset", success = success, msg = msg)

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
         },
         '/ResetPassword': {
             'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
             'tools.sessions.on': True,
             'tools.response_headers.on': True
         },
         '/ForgotPassword': {
             'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
             'tools.sessions.on': True,
             'tools.response_headers.on': True
         }
      }

webapp = Login()
webapp.login = Login()
webapp.logout = Logout()
webapp.reset = ResetPassword()
webapp.forgot = ForgotPassword()
app = cherrypy.Application(webapp, '/', config = conf)
