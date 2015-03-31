#!/usr/bin/env python

#
# Copyright 2014 Cachebox, Inc. All rights reserved. This software
# is property of Cachebox, Inc and contains trade secrects,
# confidential & proprietary information. Use, disclosure or copying
# this without explicit written permission from Cachebox, Inc is
# prohibited.
#
# Author: Cachebox, Inc (sales@stomp.com)
#

import json
import sys
import cherrypy

role = {'admin': 'admin'}

ADMIN, USER = 'admin', 'user'
roles = [ADMIN, USER]

class Unauthorized(Exception):
    def __init__(self, message = 'Request not authenticated'):
        Exception.__init__(self, message)

class Forbidden(Exception):
    def __init__(self, message = 'Request is forbidden'):
        Exception.__init__(self, message)

def authRequestHandler(fn):
    def invoke(*argv, **kwargs):
        try:
            if 'logged_in' not in cherrypy.session:
                raise Forbidden()
            return json.dumps(fn(*argv, **kwargs))
        except Unauthorized:
            raise cherrypy.HTTPError('402 Unauthorized', '%s' % sys.exc_info()[1])
        except Forbidden:
            raise cherrypy.HTTPError('403 Forbidden', '%s' % sys.exc_info()[1])
        except:
            print ("Error:")
            print ("*" * 80)
            print (sys.exc_info())
            print ("*" * 80)
            raise cherrypy.HTTPError('500 Internal Server Error', '%s' % sys.exc_info()[1])

    return invoke

def authAdminRequestHandler(fn):
    def invoke(*argv, **kwargs):
        try:
            if 'logged_in' not in cherrypy.session:
                raise Forbidden()
            if cherrypy.session['role'] != 'admin':
                raise Unauthorized()
            return json.dumps(fn(*argv, **kwargs))
        except Unauthorized:
            raise cherrypy.HTTPError('402 Unauthorized', '%s' % sys.exc_info()[1])
        except Forbidden:
            raise cherrypy.HTTPError('403 Forbidden', '%s' % sys.exc_info()[1])
        except:
            print ("Error:")
            print ("*" * 80)
            print (sys.exc_info())
            print ("*" * 80)
            raise cherrypy.HTTPError('500 Internal Server Error', '%s' % sys.exc_info()[1])

    return invoke
