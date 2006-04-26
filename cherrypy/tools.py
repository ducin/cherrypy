"""CherryPy tools. A "tool" is any helper, adapted to CP.

Tools are usually designed to be used in a variety of ways (although some
may only offer one if they choose):
    
    Library calls: all tools are callables that can be used wherever needed.
        The arguments are straightforward and should be detailed within the
        docstring.
    
    Function decorators: if the tool exposes a "wrap" callable, that is
        assumed to be a decorator for use in wrapping individual CherryPy
        page handlers (methods on the CherryPy tree). The tool may choose
        not to call the page handler at all, if the response has already
        been populated.
    
    CherryPy hooks: "hooks" are points in the CherryPy request-handling
        process which may hand off control to registered callbacks. The
        Request object possesses a "hooks" attribute for manipulating
        this. If a tool exposes a "setup" callable, this will be called
        once per Request (if the feature is enabled via config).

Tools may be implemented as any object with a namespace. The builtins
are generally either modules or instances of the tools.Tool class.
"""

import cherrypy
from cherrypy import _cputil


class HookMap(object):
    
    def __init__(self, points=None, failsafe=None):
        points = points or []
        self.callbacks = dict([(point, []) for point in points])
        self.failsafe = failsafe or []
    
    def attach(self, point, callback, conf=None):
        if conf is None:
            self.callbacks[point].append(callback)
        else:
            def wrapper():
                callback(**conf)
            self.callbacks[point].append(wrapper)
    
    def tool_config(self):
        toolmap = {}
        for k, v in cherrypy.config.current_config().iteritems():
            atoms = k.split(".")
            namespace = atoms.pop(0)
            if namespace == "tools":
                toolname = atoms.pop(0)
                bucket = toolmap.setdefault(toolname, {})
                bucket[".".join(atoms)] = v
        return toolmap
    
    def setup(self):
        """Run tool.setup(conf) for each tool specified in current config."""
        g = globals()
        for toolname, conf in self.tool_config().iteritems():
            if conf.get("on", False):
                del conf["on"]
                g[toolname].setup(conf)
        
        # Run _cp_setup_hooks functions
        mounted_app_roots = cherrypy.tree.mount_points.values()
        objectList = _cputil.get_object_trail()
        objectList.reverse()
        for objname, obj in objectList:
            s = getattr(obj, "_cp_setup_hooks", None)
            if s:
                s()
            if obj in mounted_app_roots:
                break
    
    def run(self, point):
        """Execute all registered callbacks for the given point."""
        failsafe = point in self.failsafe
        for callback in self.callbacks[point]:
            # Some hookpoints guarantee all callbacks are run even if
            # others at the same hookpoint fail. We will still log the
            # failure, but proceed on to the next callback. The only way
            # to stop all processing from one of these callbacks is
            # to raise SystemExit and stop the whole server. So, trap
            # your own errors in these callbacks!
            if failsafe:
                try:
                    callback()
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    cherrypy.log(traceback=True)
            else:
                callback()


class Tool(object):
    
    def __init__(self, point, callable):
        self.point = point
        self.callable = callable
        # TODO: add an attribute to self for each arg
        # in inspect.getargspec(callable)
    
    def __call__(self, *args, **kwargs):
        return self.callable(*args, **kwargs)
    
    def wrap(self, *args, **kwargs):
        """Make a decorator for this tool.
        
        For example:
        
            @tools.decode.wrap(encoding='chinese')
            def mandarin(self, name):
                return "%s, ni hao shi jie" % name
            mandarin.exposed = True
        """
        def deco(f):
            def wrapper(*a, **kw):
                handled = self.callable(*args, **kwargs)
                return f(*a, **kw)
            return wrapper
        return deco
    
    def setup(self, conf):
        """Hook this tool into cherrypy.request using the given conf.
        
        The standard CherryPy request object will automatically call this
        method when the tool is "turned on" in config.
        """
        cherrypy.request.hooks.attach(self.point, self.callable, conf)


class MainTool(Tool):
    """Tool which is called 'before main', that may skip normal handlers.
    
    The callable provided should return True if processing should skip
    the normal page handler, and False if it should not.
    """
    
    def __init__(self, callable):
        self.point = 'before_main'
        self.callable = callable
    
    def handler(self, *args, **kwargs):
        """Use this tool as a CherryPy page handler.
        
        For example:
            cherrypy.root.nav = tools.staticdir.handler(
                                    section="/nav", dir="nav", root=absDir)
        """
        def wrapper(*a, **kw):
            handled = self.callable(*args, **kwargs)
            if not handled:
                raise cherrypy.NotFound()
            return cherrypy.response.body
        wrapper.exposed = True
        return wrapper
    
    def wrap(self, *args, **kwargs):
        """Make a decorator for this tool.
        
        For example:
        
            @tools.staticdir.wrap(section="/slides", dir="styles", root=absDir)
            def slides(self, slide=None, style=None):
                return "No such file"
            slides.exposed = True
        """
        def deco(f):
            def wrapper(*a, **kw):
                handled = self.callable(*args, **kwargs)
                if handled:
                    return cherrypy.response.body
                else:
                    return f(*a, **kw)
            return wrapper
        return deco
    
    def setup(self, conf):
        """Hook this tool into cherrypy.request using the given conf.
        
        The standard CherryPy request object will automatically call this
        method when the tool is "turned on" in config.
        """
        def wrapper():
            if self.callable(**conf):
                cherrypy.request.execute_main = False
        # Don't pass conf (or our wrapper will get wrapped!)
        cherrypy.request.hooks.attach(self.point, wrapper)


#                              Builtin tools                              #

from cherrypy.lib import cptools
session_auth = MainTool(cptools.session_auth)
base_url = Tool('before_request_body', cptools.base_url)
response_headers = Tool('before_finalize', cptools.response_headers)
virtual_host = Tool('before_request_body', cptools.virtual_host)
del cptools

from cherrypy.lib import encodings
decode = Tool('before_main', encodings.decode)
encode = Tool('before_finalize', encodings.encode)
gzip = Tool('before_finalize', encodings.gzip)
del encodings

from cherrypy.lib import static
class _StaticDirTool(MainTool):
    def setup(self, conf):
        """Hook this tool into cherrypy.request using the given conf."""
        conf['section'] = cherrypy.config.get('tools.staticdir.dir',
                                              return_section=True)
        def wrapper():
            if self.callable(**conf):
                cherrypy.request.execute_main = False
        # Don't pass conf (or our wrapper will get wrapped!)
        cherrypy.request.hooks.attach(self.point, wrapper)
staticdir = _StaticDirTool(static.get_dir)
staticfile = MainTool(static.get_file)
del static

# These modules are themselves Tools
from cherrypy.lib import caching, sessions, xmlrpc