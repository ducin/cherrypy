"""A WSGI application interface (see PEP 333)."""
import logging
import sys

import cherrypy
from cherrypy import _cpwsgiserver, config
from cherrypy._cperror import format_exc, bare_error
from cherrypy.lib import http


headerNames = {'HTTP_CGI_AUTHORIZATION': 'Authorization',
               'CONTENT_LENGTH': 'Content-Length',
               'CONTENT_TYPE': 'Content-Type',
               'REMOTE_HOST': 'Remote-Host',
               'REMOTE_ADDR': 'Remote-Addr',
               }

def translate_headers(environ):
    """Translate CGI-environ header names to HTTP header names."""
    for cgiName in environ:
        # We assume all incoming header keys are uppercase already.
        if cgiName in headerNames:
            yield headerNames[cgiName], environ[cgiName]
        elif cgiName[:5] == "HTTP_":
            # Hackish attempt at recovering original header names.
            translatedHeader = cgiName[5:].replace("_", "-")
            yield translatedHeader, environ[cgiName]

def _init_request(environ):
    """Initialize and return the cherrypy.request object."""
    env = environ.get
    local = http.Host('', int(env('SERVER_PORT', 80)),
                      env('SERVER_NAME', ''))
    remote = http.Host(env('REMOTE_ADDR', ''),
                       int(env('REMOTE_PORT', -1)),
                       env('REMOTE_HOST', ''))
    request = cherrypy.engine.request(local, remote, env('wsgi.url_scheme'))
    return request

class Application:
    """A CherryPy WSGI Application."""
    
    def __init__(self, root, script_name="", conf=None):
        self.access_log = log = logging.getLogger("cherrypy.access.%s" % id(self))
        log.setLevel(logging.INFO)
        
        self.error_log = log = logging.getLogger("cherrypy.error.%s" % id(self))
        log.setLevel(logging.DEBUG)
        
        self.root = root
        self.script_name = script_name
        self.conf = {}
        if conf:
            self.merge(conf)

    def __call__(self, environ, start_response):
        if not getattr(cherrypy.request, 'initialized', False):
            request = _init_request(environ)
        else:
            request = cherrypy.request
        try:
            
            env = environ.get
            # LOGON_USER is served by IIS, and is the name of the
            # user after having been mapped to a local account.
            # Both IIS and Apache set REMOTE_USER, when possible.
            request.login = env('LOGON_USER') or env('REMOTE_USER') or None
            
            request.multithread = environ['wsgi.multithread']
            request.multiprocess = environ['wsgi.multiprocess']
            request.wsgi_environ = environ
            request.app = self
            
            path = environ.get('SCRIPT_NAME', '') + environ.get('PATH_INFO', '')
            response = request.run(environ['REQUEST_METHOD'], path,
                                   environ.get('QUERY_STRING'),
                                   environ.get('SERVER_PROTOCOL'),
                                   translate_headers(environ),
                                   environ['wsgi.input'])
            s, h, b = response.status, response.header_list, response.body
            exc = None
        except (KeyboardInterrupt, SystemExit), ex:
            try:
                if request:
                    request.close()
            except:
                cherrypy.log(traceback=True)
            request = None
            raise ex
        except:
            if cherrypy.config.get("throw_errors", False):
                raise
            tb = format_exc()
            cherrypy.log(tb)
            if not cherrypy.config.get("show_tracebacks", False):
                tb = ""
            s, h, b = bare_error(tb)
            exc = sys.exc_info()
        
        try:
            start_response(s, h, exc)
            for chunk in b:
                # WSGI requires all data to be of type "str". This coercion should
                # not take any time at all if chunk is already of type "str".
                # If it's unicode, it could be a big performance hit (x ~500).
                if not isinstance(chunk, str):
                    chunk = chunk.encode("ISO-8859-1")
                yield chunk
            if request:
                request.close()
            request = None
        except (KeyboardInterrupt, SystemExit), ex:
            try:
                if request:
                    request.close()
            except:
                cherrypy.log(traceback=True)
            request = None
            raise ex
        except:
            cherrypy.log(traceback=True)
            try:
                if request:
                    request.close()
            except:
                cherrypy.log(traceback=True)
            request = None
            s, h, b = bare_error()
            # CherryPy test suite expects bare_error body to be output,
            # so don't call start_response (which, according to PEP 333,
            # may raise its own error at that point).
            for chunk in b:
                if not isinstance(chunk, str):
                    chunk = chunk.encode("ISO-8859-1")
                yield chunk
    
    def merge(self, conf):
        """Merge the given config into self.config."""
        config.merge(self.conf, conf)
        
        # Create log handlers as specified in config.
        rootconf = self.conf.get("/", {})
        config._configure_builtin_logging(rootconf, self.access_log, "log_access_file")
        config._configure_builtin_logging(rootconf, self.error_log)
    
    def guess_abs_path(self):
        """Guess the absolute URL from server.socket_host and script_name.
        
        When inside a request, the abs_path can be formed via:
            cherrypy.request.base + (cherrypy.request.app.script_name or "/")
        
        However, outside of the request we must guess, hoping the deployer
        set socket_host and socket_port correctly.
        """
        port = int(config.get('server.socket_port', 80))
        if port in (443, 8443):
            scheme = "https://"
        else:
            scheme = "http://"
        host = config.get('server.socket_host', '')
        if port != 80:
            host += ":%s" % port
        return scheme + host + self.script_name

class HostedWSGI(object):
    def __init__(self, app):
        self.app = app
        self._cp_config = {'tools.wsgiapp.on': True,
                           'tools.wsgiapp.app': app,
                          }


#                            Server components                            #


class CPHTTPRequest(_cpwsgiserver.HTTPRequest):
    
    def __init__(self, socket, addr, server):
        _cpwsgiserver.HTTPRequest.__init__(self, socket, addr, server)
        mhs = int(cherrypy.config.get('server.max_request_header_size',
                                      500 * 1024))
        if mhs > 0:
            self.rfile = http.SizeCheckWrapper(self.rfile, mhs)
    
    def parse_request(self):
        try:
            _cpwsgiserver.HTTPRequest.parse_request(self)
        except http.MaxSizeExceeded:
            msg = "Request Entity Too Large"
            self.wfile.write("%s 413 %s\r\n" % (self.server.protocol, msg))
            self.wfile.write("Content-Length: %s\r\n\r\n" % len(msg))
            self.wfile.write(msg)
            self.wfile.flush()
            self.ready = False
            
            cherrypy.log(traceback=True)
        else:
            if self.ready:
                # Request header is parsed
                script_name = self.environ.get('SCRIPT_NAME', '')
                path_info = self.environ.get('PATH_INFO', '')
                path = (script_name + path_info)
                if path == "*":
                    path = "global"
                
                if isinstance(self.rfile, http.SizeCheckWrapper):
                    # Unwrap the rfile
                    self.rfile = self.rfile.rfile
                self.environ["wsgi.input"] = self.rfile


class WSGIServer(_cpwsgiserver.CherryPyWSGIServer):
    
    """Wrapper for _cpwsgiserver.CherryPyWSGIServer.
    
    _cpwsgiserver has been designed to not reference CherryPy in any way,
    so that it can be used in other frameworks and applications. Therefore,
    we wrap it here, so we can set our own mount points from cherrypy.tree.
    
    """
    
    RequestHandlerClass = CPHTTPRequest
    
    def __init__(self):
        conf = cherrypy.config.get
        
        sockFile = conf('server.socket_file')
        if sockFile:
            bind_addr = sockFile
        else:
            bind_addr = (conf('server.socket_host'),
                         conf('server.socket_port'))
        
        app = cherrypy.tree.dispatch
        
        s = _cpwsgiserver.CherryPyWSGIServer
        s.__init__(self, bind_addr, app,
                   conf('server.thread_pool'),
                   conf('server.socket_host'),
                   request_queue_size = conf('server.socket_queue_size'),
                   timeout = conf('server.socket_timeout'),
                   )
        s.protocol = conf('server.protocol_version', 'HTTP/1.0')

