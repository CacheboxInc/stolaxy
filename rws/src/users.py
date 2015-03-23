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
from src.util import *

sys.path.append(os.getcwd() + "/../spmc")
from user import User

from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('./templates'))

class Users(object):
    exposed = True

    applications = [
                {'id': 1,
                 'created': '2015-03-11 11:12:49',
                 'modified': '2015-03-13 17:12:49',
                 'atype': 1,
                 'astate': 'play' 
                },
                {'id': 2,
                 'created': '2015-03-11 11:12:49',
                 'modified': '2015-03-13 17:12:49',
                 'atype': 1,
                 'astate': 'pause'
                },
                {'id': 3,
                 'created': '2015-03-11 11:12:49',
                 'modified': '2015-03-13 17:12:49',
                 'atype': 1,
                 'astate': 'stop'
                },
                {'id': 4,
                 'created': '2015-03-11 11:12:49',
                 'modified': '2015-03-13 17:12:49',
                 'atype': 1,
                 'astate': 'stop'
                },
            ]
    @authAdminRequestHandler
    def GET(self, arg, id=None):
        users = []
        if arg == 'nongrouplist':
            #Fetch only users that are not added to any group.
            if id is not None:
                allusers = User.nongrouplisting(id)
            else:
                allusers = User.nongrouplisting()

            for user in allusers:
                u = user.to_dict()
                u['applications'] = self.applications
                users.append(u)
        else:
            #Fetch all users whether added to group or not.
            for user in User.listing():
                u = user.to_dict()
                u['applications'] = self.applications
                users.append(u)

        return {'users': users}

    def create(self, **data):
        User.create_or_get(**data)

    def delete(self, user_id):
        User.delete(user_id)

    def update(self, **data):
        User.update(**data)

    @cherrypy.tools.json_in()
    @authAdminRequestHandler
    def POST(self, op):
        data = cherrypy.request.json
        error = False
        userobj = False 
        resp = {}

        if op == 'create':
            username = data.get("username", None)
            email = data.get("email", None)

            # Check if user with given email or username
            # already exists in DB.
            if User.get(username) is not False:
                msg = "Username %s already exists." % username
                error = True
            elif User.get_by_email(email) is not False:
                msg = "Email %s already exists." % email
                error = True
            else:
                # We need to send this password via email.
                temp_pwd = generate_random_password()

                # Generate encrypted password
                enc_pwd = generate_password(temp_pwd)

                data['password'] = enc_pwd
                user = self.create(**data)

                userobj = User.get(username)

                #Send an email to user on successful creation.
                template = env.get_template('email-content.html')
                template_data = {}
                template_data['fullname'] = userobj.fullname
                template_data['email'] = userobj.email
                template_data['password'] = temp_pwd
                content = template.render(user=template_data)
                try:
                    send_email(content, userobj.email)
                except:
                    # We can't send email all the time in development.
                    # Let's skip for now
                    pass

                msg = "User %s created successfully" % userobj.fullname,

        elif op == 'delete':
            user_id = data.get('id')
            userobj = User.get_by_id(user_id)
            self.delete(user_id)
            msg = "User %s deleted successfully" % userobj.fullname,
        
        elif op == 'update':
            userid = int(data.get('id', 0))
            username = data.get("username", None)
            email = data.get("email", None)
            user = User.get(username)
            if user is not False:
                if user.id != userid:
                    msg = "Username %s already exists." % username
                    error = True

            if not error:
                user = User.get_by_email(email)
                if user is not False:
                    if user.id != userid:
                        msg = "Email %s already exists." % email
                        error = True

            if not error:
                self.update(**data)
                userobj = User.get_by_id(userid)
                msg = "User %s updated successfully" % userobj.fullname,

        resp['msg'] = msg
        resp['error'] = error
        if userobj is not False:
            userobj.applications = self.applications
            users = {}
            users['id'] = userobj.id
            users['fullname'] = userobj.fullname
            users['username'] = userobj.username
            users['email'] = userobj.email
            users['firstlogin'] = str(userobj.firstlogin)
            users['lastlogin'] = str(userobj.lastlogin)
            users['created'] = str(userobj.created)
            users['modified'] = str(userobj.modified)
            users['group'] = userobj.group_id
            users['login_count'] = userobj.login_count
            users['online'] = userobj.online
            users['role'] = userobj.role
            users['applications'] = userobj.applications
            resp['users'] = [users]
        return resp

conf = {
         '/': {
             'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
             'tools.sessions.on': True,
             'tools.response_headers.on': True
         }
      }

app = cherrypy.Application(Users(), '/user', config = conf)
