from cherrypy._cperror import format_exc, bare_error
from cherrypy._cpwsgi import Application, HostedWSGI
from cherrypy import NotFound
from cherrypy.lib import http


class Tree:
    """A dispatcher of WSGI applications, mounted at diverse points."""
    
    def __init__(self):
        self.apps = {}
    
    def mount(self, app, script_name="", conf=None, wrap=True):
        """Mount a new app at script_name using configuration in conf.
        
        An application can be one of:
            1) A standard cherrypy.Application - left as is.
            2) A "root" object - wrapped in an Application instance.
            3) A  WSGI callable - optionally wrapped in a HostedWSGI instance.
        
        If wrap == True, a WSGI callable will be wrapped in a cherrypy.Application
        instance, allowing the use of tools with the WSGI application.
        """
        
        # Next line both 1) strips trailing slash and 2) maps "/" -> "".
        script_name = script_name.rstrip("/")
        
        # Leave Application objects alone
        if isinstance(app, Application):
            pass
        # Handle "root" objects...
        elif not callable(app):
            app = Application(app, script_name, conf)
        # Handle WSGI callables
        elif callable(app) and wrap:
            app = Application(HostedWSGI(app), script_name, conf)
        # In all other cases leave the app intact (no wrapping)
        
        self.apps[script_name] = app
        
        # If mounted at "", add favicon.ico
        if script_name == "" and app and not hasattr(app, "favicon_ico"):
            import os
            from cherrypy import tools
            favicon = os.path.join(os.getcwd(), os.path.dirname(__file__),
                                   "favicon.ico")
            app.favicon_ico = tools.staticfile.handler(favicon)
        
        return app
    
    def script_name(self, path=None):
        """The script_name of the app at the given path, or None.
        
        If path is None, cherrypy.request.path is used.
        """
        
        if path is None:
            try:
                import cherrypy
                path = cherrypy.request.path
            except AttributeError:
                return None
        
        while True:
            if path in self.apps:
                return path
            
            if path == "":
                return None
            
            # Move one node up the tree and try again.
            path = path[:path.rfind("/")]
    
    def url(self, path, script_name=None):
        """Return 'path', prefixed with script_name.
        
        If script_name is None, cherrypy.request.path will be used
        to find a script_name.
        """
        
        if script_name is None:
            script_name = self.script_name()
            if script_name is None:
                return path
        
        from cherrypy.lib import http
        return http.urljoin(script_name, path)

    def dispatch(self, environ, start_response):
        """Dispatch to mounted WSGI applications."""
        script_name = environ.get("SCRIPT_NAME", '').rstrip('/')
        path_info = environ.get("PATH_INFO", '')
        
        mount_points = self.apps.keys()
        mount_points.sort()
        mount_points.reverse()
        
        for mp in mount_points:
            if path_info.startswith(mp):
                environ['SCRIPT_NAME'] = script_name + mp
                environ['PATH_INFO'] = path_info[len(mp):]
                app = self.apps[mp]
                return app(environ, start_response)
        raise NotFound
