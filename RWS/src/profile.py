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
import web

from auth import authRequestHandler

class Profile:

    users = {
               'id': random.randint(1, 100),
               'created': '19 Jan 2015 12:01:09',
               'modified': '20 Jan 2015 23:11:10',
               'name': 'user1',
               'group_id': random.randint(1, 100),
               'group': 'group1' 
             }

    @authRequestHandler
    def GET(self, arg):
        return {'users': self.users}

    @authRequestHandler
    def POST(self, op):
        data = web.input()
        user_id = data.user_id
        name = data.user_name
        return {
                'msg': "User %s successfully updated" % name,
                'users':[
                {
                  'id': user_id,
                  'created': '19 Jan 2015 12:01:09',
                  'modified': '20 Jan 2015 23:11:10',
                  'name': name,
                  'group_id': random.randint(1, 100),
                  'group': 'group1' 
                }
               ]
        }
 
urls = (
        "/(.*)", "Profile"
       )

app_user = web.application(urls, locals())
