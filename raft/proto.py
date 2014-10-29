ENTRY_CONFIGURATION = 1
ENTRY_DATA = 2
ENTRY_NOOP = 3

class Entry(object):
    def __init__(self):
        self.term = None
        self.type = None
        self.configuration = None
        self.data = None

    def set_term(self, term):
        self.term = term

    def set_type(self, type):
        assert type in [ENTRY_CONFIGURATION, ENTRY_DATA, ENTRY_NOOP]
        self.type = type


class Server(object):
    def set_server_id(self, server_id):
        self.server_id = server_id

    def set_address(self, address):
        self.address = address


class RequestVote(object):
    pass

