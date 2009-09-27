"""Native adapter for serving CherryPy via its builtin server."""

import logging
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import cherrypy
from cherrypy._cperror import format_exc, bare_error
from cherrypy.lib import httputil
from cherrypy import wsgiserver


class NativeGateway(wsgiserver.Gateway):
    
    recursive = False
    
    def respond(self):
        req = self.req
        try:
            # Obtain a Request object from CherryPy
            local = req.server.bind_addr
            local = httputil.Host(local[0], local[1], "")
            remote = req.conn.remote_addr, req.conn.remote_port
            remote = httputil.Host(remote[0], remote[1], "")
            
            scheme = req.scheme
            sn = cherrypy.tree.script_name(req.uri or "/")
            if sn is None:
                self.send_response('404 Not Found', [], [''])
            else:
                app = cherrypy.tree.apps[sn]
                method = req.method
                path = req.path
                qs = req.qs or ""
                headers = req.inheaders.items()
                rfile = req.rfile
                prev = None
                
                try:
                    redirections = []
                    while True:
                        request, response = app.get_serving(
                            local, remote, scheme, "HTTP/1.1")
                        request.multithread = True
                        request.multiprocess = False
                        request.app = app
                        request.prev = prev
                        
                        # Run the CherryPy Request object and obtain the response
                        try:
                            request.run(method, path, qs, req.request_protocol, headers, rfile)
                            break
                        except cherrypy.InternalRedirect, ir:
                            app.release_serving()
                            prev = request
                            
                            if not self.recursive:
                                if ir.path in redirections:
                                    raise RuntimeError("InternalRedirector visited the "
                                                       "same URL twice: %r" % ir.path)
                                else:
                                    # Add the *previous* path_info + qs to redirections.
                                    if qs:
                                        qs = "?" + qs
                                    redirections.append(sn + path + qs)
                            
                            # Munge environment and try again.
                            method = "GET"
                            path = ir.path
                            qs = ir.query_string
                            rfile = StringIO()
                    
                    self.send_response(
                        response.output_status, response.header_list,
                        response.body)
                finally:
                    app.release_serving()
        except:
            tb = format_exc()
            #print tb
            cherrypy.log(tb, 'NATIVE_ADAPTER', severity=logging.ERROR)
            s, h, b = bare_error()
            self.send_response(s, h, b)
    
    def send_response(self, status, headers, body):
        req = self.req
        
        # Set response status
        req.status = str(status or "500 Server Error")
        
        # Set response headers
        for header, value in headers:
            req.outheaders.append((header, value))
        if (req.ready and not req.sent_headers):
            req.sent_headers = True
            req.send_headers()
        
        # Set response body
        for seg in body:
            req.write(seg)

