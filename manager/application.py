#!/usr/bin/env python3

import getopt
import sys

from configdb import *

class Application(object):
    application_ops = [
        "create",
        "delete",
        "help",
        "list",
        "pause",
        "unpause",
        "start",
        "stop",
        "snapshot",
        "backup",
        ]

    application_states = {
        'POWERED_OFF':0,
        'POWERED_ON':1,
        'PAUSED':2,
        'COMPONENT_ERROR':3, # if any of the containers have a fault
        }

    application_states_print = {v: k for k, v in application_states.items()}

    def create(self, **kwargs):
        raise Exception("application does not support create interface")

    def delete(self, **kwargs):
        raise Exception("application does not support delete interface")

    def list(self, **kwargs):
        raise Exception("application does not support list interface")

    def get(self, **kwargs):
        raise Exception("application does not support get interface")
        pass

    def pause(self, **kwargs):
        raise Exception("application does not support pause interface")
        pass

    def unpause(self, **kwargs):
        raise Exception("application does not support unpause interface")
        pass

    def stop(self, **kwargs):
        raise Exception("application does not support stop interface")
        pass

    def start(self, **kwargs):
        raise Exception("application does not support start interface")
        pass

    def snapshot(self, **kwargs):
        raise Exception("application does not support snapshot interface")
        pass

    def backup(self, **kwargs):
        raise Exception("application does not support backup interface")
        pass
