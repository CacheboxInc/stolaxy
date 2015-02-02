import uuid

from configdb import Base, session

class Cluster(object):
    def __init__(self, id = None):
        self.id = id
        

    def put(self):
        if self.id is None:

            #
            # create a new cluster object
            #

            self.id = uuid.uuid4().hex
            
