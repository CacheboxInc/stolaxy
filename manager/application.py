#!/usr/bin/env python3

class Application(object):
    application_states = {
        'POWERED_OFF':0,
        'POWERED_ON':1,
        'PAUSED':2,
        'COMPONENT_ERROR':3, # if any of the containers have a fault
        }
    
    @classmethod
    def create(cls, **kwargs):
        pass

    @classmethod
    def delete(cls, **kwargs):
        pass

    @classmethod
    def get(cls, **kwargs):
        pass
