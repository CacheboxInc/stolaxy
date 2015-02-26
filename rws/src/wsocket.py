import time
class StompWebSocketHandler(object):

    @classmethod
    def on_open(cls):
        time.sleep(10)
        return("data", False)
    
    @classmethod
    def on_receive(cls, message):
        return (message.data, message.is_binary)
