import cherrypy
import mimetypes
from src import home
from src import hosts
from src import application
from src import groups
from src import users
from src import storage

import os

WEBAPP_PORT = 8080
WEBSOCKET_PORT = 9786

mimetypes.types_map['.ttf'] = 'font/opentype'
mimetypes.types_map['.woff2'] = 'font/opentype'

def secureheaders():
    headers = cherrypy.response.headers
    headers['X-Frame-Options'] = 'DENY'
    headers['X-XSS-Protection'] = '1; mode=block'
    headers['Content-Security-Policy'] = "default-src='self'"
    headers['Strict-Transport-Security'] = 'max-age=31536000'

cherrypy.tools.secureheaders = cherrypy.Tool('before_finalize', secureheaders, priority=60)

cherrypy.config.update({
                        'tools.secureheaders.on': True,
                        'tools.sessions.on': True,
                        'tools.sessions.storage_type': "file",
                        'tools.sessions.storage_path': "./web_session/",
                        'tools.sessions.secure': False,
                        'tools.staticdir.on': True,
                        'tools.staticdir.root': os.getcwd(),
                        'tools.staticdir.dir': "./",
                        'tools.encode.encoding': "utf-8",
                        'tools.json_in.on': True,
                        'tools.json_in.force': False,
                        'server.socket_host': "0.0.0.0",
                        'server.socket_port': WEBAPP_PORT,
                        #'server.ssl_module': 'builtin',
                        #'server.ssl_certificate': 'server_cert.pem',
                        #'server.ssl_private_key': 'server_key.pem'
                      })

cherrypy.tree.mount(home.app)
cherrypy.tree.mount(hosts.app)
cherrypy.tree.mount(application.app)
cherrypy.tree.mount(groups.app)
cherrypy.tree.mount(users.app)
cherrypy.tree.mount(storage.app)
