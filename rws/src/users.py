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
                 'name': 'App-1',
                 'created': '2015-03-11 11:12:49',
                 'modified': '2015-03-13 17:12:49',
                 'atype': 'MAPREDUCE',
                 'astate': 'play' 
                },
                {'id': 2,
                 'name': 'App-2',
                 'created': '2015-03-11 11:12:49',
                 'modified': '2015-03-13 17:12:49',
                 'atype': 'HIVE',
                 'astate': 'pause'
                },
                {'id': 3,
                 'name': 'App-3',
                 'created': '2015-03-11 11:12:49',
                 'modified': '2015-03-13 17:12:49',
                 'atype': 'HIVE',
                 'astate': 'stop'
                },
                {'id': 4,
                 'name': 'App-4',
                 'created': '2015-03-11 11:12:49',
                 'modified': '2015-03-13 17:12:49',
                 'atype': 'PIG',
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
        return User.create_or_get(**data)

    def delete(self, user_id):
        return User.delete(user_id)

    def update(self, **data):
        return User.update(**data)

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

                userobj = user.to_dict()

                #Send an email to user on successful creation.
                template = env.get_template('email-content.html')
                template_data = {}
                template_data['fullname'] = userobj.get('fullname', None)
                template_data['email'] = userobj.get('email', None)
                template_data['password'] = temp_pwd
                content = template.render(user=template_data)
                try:
                    send_email(content, userobj.get('email'))
                except:
                    # We can't send email all the time in development.
                    # Let's skip for now
                    pass

                msg = "User %s created successfully" % userobj.get('fullname', ''),

        elif op == 'delete':
            user_id = data.get('id')
            self.delete(user_id)
            msg = "User deleted successfully" 
        
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
                user = self.update(**data)
                userobj = user.to_dict()
                msg = "User %s updated successfully" % userobj.get('fullname', ''),


        return {
                'msg': msg,
                'error': error,
                'users': [userobj]
        }

conf = {
         '/': {
             'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
             'tools.sessions.on': True,
             'tools.response_headers.on': True
         }
      }

app = cherrypy.Application(Users(), '/user', config = conf)
