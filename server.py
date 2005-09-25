"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

"""
Main CherryPy module:
    - Creates a server
"""

import warnings
import threading
import time
import sys

import cherrypy
from cherrypy import _cphttptools
from cherrypy.lib import autoreload, profiler


# Set some special attributes for adding hooks
onStartServerList = []
onStartThreadList = []
onStopServerList = []
onStopThreadList = []


def start(initOnly=False, serverClass=None):
    defaultOn = (cherrypy.config.get("server.environment") == "development")
    if cherrypy.config.get('autoreload.on', defaultOn):
        # Check initOnly. If True, we're probably not starting
        # our own webserver, and therefore could do Very Bad Things
        # when autoreload calls sys.exit.
        if not initOnly:
            try:
                autoreload.main(_start, (initOnly, serverClass))
            except KeyboardInterrupt:
                cherrypy.log("<Ctrl-C> hit: shutting down autoreloader", "HTTP")
            return
    
    _start(initOnly, serverClass)

def _start(initOnly=False, serverClass=None):
    """
        Main function. All it does is this:
            - output config options
            - create response and request objects
            - starts a server
            - initilizes built in filters
    """
    
    if cherrypy.codecoverage:
        from cherrypy.lib import covercp
        covercp.start()
    
    # Use a flag to indicate the state of the cherrypy application server.
    # 0 = Not started
    # None = In process of starting
    # 1 = Started, ready to receive requests
    cherrypy._appserver_state = None
    
    # Output config options to log
    if cherrypy.config.get("server.logConfigOptions", True):
        cherrypy.config.outputConfigMap()
    
    # Check the config options
    # TODO
    # config.checkConfigOptions()
    
    # If sessions are stored in files and we
    # use threading, we need a lock on the file
    if (cherrypy.config.get('server.threadPool') > 1
        and cherrypy.config.get('session.storageType') == 'file'):
        cherrypy._sessionFileLock = threading.RLock()
    
    # set cgi.maxlen which will limit the size of POST request bodies
    import cgi
    cgi.maxlen = cherrypy.config.get('server.maxRequestSize')
    
    # Call the functions from cherrypy.server.onStartServerList
    for func in cherrypy.server.onStartServerList:
        func()
    
    # Set up the profiler if requested.
    if cherrypy.config.get("profiling.on", False):
        ppath = cherrypy.config.get("profiling.path", "")
        cherrypy.profiler = profiler.Profiler(ppath)
    else:
        cherrypy.profiler = None

    # Initilize the built in filters
    cherrypy._cputil._cpInitDefaultFilters()
    cherrypy._cputil._cpInitUserDefinedFilters()
    
    if initOnly:
        cherrypy._appserver_state = 1
    else:
        run_server(serverClass)

def check_port(host, port):
    """Raise an error if the given port is not free on the given host."""
    
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, int(port)))
        s.close()
        raise IOError("Port %s is in use on %s; perhaps the previous "
                      "server did not shut down properly." % (port, host))
    except socket.error:
        pass

def run_server(serverClass=None):
    """Prepare the requested server and then run it."""
    
    if cherrypy._httpserver is not None:
        warnings.warn("You seem to have an HTTP server still running."
                      "Please call cherrypy.server.stop() before continuing.")
    
    # Instantiate the server.
    if serverClass is None:
        serverClass = cherrypy.config.get("server.class", None)
    if serverClass and isinstance(serverClass, basestring):
        serverClass = cherrypy._cputil.attributes(serverClass)
    if serverClass is None:
        import _cpwsgi
        serverClass = _cpwsgi.WSGIServer
    
    if cherrypy.config.get('server', 'socketPort'):
        host = cherrypy.config.get('server.socketHost')
        port = cherrypy.config.get('server.socketPort')
        check_port(host, port)
        if not host:
            host = 'localhost'
        onWhat = "http://%s:%s/" % (host, port)
    else:
        onWhat = "socket file: %s" % cherrypy.config.get('server.socketFile')
    cherrypy.log("Serving HTTP on %s" % onWhat, 'HTTP')
    
    # Start the http server. This must be done after check_port, above.
    cherrypy._httpserver = serverClass()
    try:
        try:
            cherrypy._appserver_state = 1
            # This should block until the http server stops.
            cherrypy._httpserver.start()
        except (KeyboardInterrupt, SystemExit):
            pass
    finally:
        cherrypy.log("<Ctrl-C> hit: shutting down", "HTTP")
        stop()


seen_threads = {}

def request(clientAddress, remoteHost, requestLine, headers, rfile, scheme="http"):
    """request(clientAddress, remoteHost, requestLine, headers, rfile, scheme="http")
    
    clientAddress: the (IP address, port) of the client
    remoteHost: the IP address of the client
    requestLine: "<HTTP method> <url?qs> HTTP/<version>",
            e.g. "GET /main?abc=123 HTTP/1.1"
    headers: a list of (key, value) tuples
    rfile: a file-like object from which to read the HTTP request body
    scheme: either "http" or "https"; defaults to "http"
    """
    if cherrypy._appserver_state == 0:
        raise cherrypy.NotReady("No thread has called cherrypy.server.start().")
    
    trials = 0
    while cherrypy._appserver_state == None:
        # Give the server thread time to complete.
        trials += 1
        if trials > 10:
            raise cherrypy.NotReady("cherrypy.server.start() encountered errors.")
        time.sleep(1)
    
    threadID = threading._get_ident()
    if threadID not in seen_threads:
        
        if cherrypy.codecoverage:
            from cherrypy.lib import covercp
            covercp.start()
        
        i = len(seen_threads) + 1
        seen_threads[threadID] = i
        # Call the functions from cherrypy.server.onStartThreadList
        for func in cherrypy.server.onStartThreadList:
            func(i)
    
    if cherrypy.profiler:
        cherrypy.profiler.run(_cphttptools.Request, clientAddress, remoteHost,
                              requestLine, headers, rfile, scheme)
    else:
        _cphttptools.Request(clientAddress, remoteHost,
                             requestLine, headers, rfile, scheme)

def stop():
    """Shutdown CherryPy (and any HTTP servers it started)."""
    try:
        httpstop = cherrypy._httpserver.stop
    except AttributeError:
        pass
    else:
        httpstop()
    
    # Call the functions from cherrypy.server.onStopThreadList
    for thread_ident, i in seen_threads.iteritems():
        for func in cherrypy.server.onStopThreadList:
            func(i)
    seen_threads.clear()
    
    # Call the functions from cherrypy.server.onStopServerList
    for func in cherrypy.server.onStopServerList:
        func()
    
    cherrypy._httpserver = None
    cherrypy._appserver_state = 0

def restart():
    """Stop and start CherryPy."""
    http = getattr(cherrypy, '_httpserver', None)
    if http:
        stop()
        # Give HTTP servers time to shut down their thread pools.
        time.sleep(1)
        # Start the server in a new thread
        thread_args = {"serverClass": http.__class__}
        threading.Thread(target=_start, kwargs=thread_args).start()
    else:
        stop()
        _start(initOnly=True)