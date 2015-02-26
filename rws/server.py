import cherrypy
from config import *
import os
import sys
import threading

from daemon import Daemon
from src.wsocket import StompWebSocketHandler
from wsgiref.simple_server import make_server
from ws4py.websocket import WebSocket
from ws4py.server.wsgirefserver import WSGIServer, WebSocketWSGIRequestHandler
from ws4py.server.wsgiutils import WebSocketWSGIApplication

LOGFILE = "/var/log/stolaxy/server.log"
PIDFILE = "/var/log/stolaxy/server.pid"

class ServerDaemon(Daemon):
    def run(self):
        if hasattr(cherrypy.engine, 'block'):
            # 3.1 syntax
            cherrypy.engine.start()
            cherrypy.engine.block()
        else:
            # 3.0 syntax
            cherrypy.server.quickstart()
            cherrypy.engine.start()

class StompWebSocket(WebSocket):
    def received_message(self, message):
        data, is_binary = StompWebSocketHandler.on_receive(message)
        self.send(data, is_binary)

    def opened(self):
        while True:
            data, is_binary = StompWebSocketHandler.on_open()
            self.send(data, is_binary)

def open_websocket():
    server = make_server('0.0.0.0', WEBSOCKET_PORT, server_class=WSGIServer,
                         handler_class=WebSocketWSGIRequestHandler,
                         app=WebSocketWSGIApplication(handler_cls=StompWebSocket))
    server.initialize_websockets_manager()
    server.serve_forever()

if __name__ == '__main__':
    wsocket = threading.Thread(
           target = open_websocket,
    )
    wsocket.start()
    path = os.getcwd()
    daemon = ServerDaemon(PIDFILE, stdout=LOGFILE, stderr=LOGFILE, chdir=path)
    daemon.run()
    if len(sys.argv) == 2:
        if cmd == 'start':
            daemon.start()
        elif cmd == 'stop':
            daemon.stop()
        elif cmd == 'restart':
            daemon.restart()
    wsocket.join()
    sys.exit(0)
