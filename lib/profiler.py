"""Profiler tools for CherryPy.

CherryPy users
==============

You can profile any of your pages as follows:

    from cherrypy.lib import profile
    
    class Root:
        p = profile.Profiler("/path/to/profile/dir")
        
        def index(self):
            self.p.run(self._index)
        index.exposed = True
        
        def _index(self):
            return "Hello, world!"
    
    cherrypy.root = Root()


CherryPy developers
===================

This module can be used whenever you make changes to CherryPy, to get a
quick sanity-check on overall CP performance. Set the config entry:
"profiling.on = True" to turn on profiling. Then, use the serve()
function to browse the results in a web browser. If you run this
module from the command line, it will call serve() for you.

"""


import hotshot
import os, os.path
import sys

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


class Profiler(object):
    
    def __init__(self, path=None):
        if not path:
            path = os.path.join(os.path.dirname(__file__), "profile")
        self.path = path
        if not os.path.exists(path):
            os.makedirs(path)
        self.count = 0
    
    def run(self, func, *args):
        """run(func, *args). Run func, dumping profile data into self.path."""
        self.count += 1
        path = os.path.join(self.path, "cp_%04d.prof" % self.count)
        prof = hotshot.Profile(path)
        prof.runcall(func, *args)
        prof.close()
    
    def statfiles(self):
        """statfiles() -> list of available profiles."""
        return [f for f in os.listdir(self.path)
                if f.startswith("cp_") and f.endswith(".prof")]
    
    def stats(self, filename, sortby='cumulative'):
        """stats(index) -> output of print_stats() for the given profile."""
        from hotshot.stats import load
        s = load(os.path.join(self.path, filename))
        s.strip_dirs()
        s.sort_stats(sortby)
        oldout = sys.stdout
        try:
            sys.stdout = sio = StringIO.StringIO()
            s.print_stats()
        finally:
            sys.stdout = oldout
        response = sio.getvalue()
        sio.close()
        return response
    
    def index(self):
        return """<html>
        <head><title>CherryPy profile data</title></head>
        <frameset cols='200, 1*'>
            <frame src='menu' />
            <frame name='main' src='' />
        </frameset>
        </html>
        """
    index.exposed = True
    
    def menu(self):
        yield "<h2>Profiling runs</h2>"
        yield "<p>Click on one of the runs below to see profiling data.</p>"
        runs = self.statfiles()
        runs.sort()
        for i in runs:
            yield "<a href='report?filename=%s' target='main'>%s</a><br />" % (i, i)
    menu.exposed = True
    
    def report(self, filename):
        import cherrypy
        cherrypy.response.headerMap['Content-Type'] = 'text/plain'
        return self.stats(filename)
    report.exposed = True


def serve(path=None, port=8080):
    import cherrypy
    cherrypy.root = Profiler(path)
    cherrypy.config.update({'server.socketPort': port,
                            'server.threadPool': 10,
                            'server.environment': "production",
                            'session.storageType': "ram",
                            })
    cherrypy.server.start()


if __name__ == "__main__":
    serve(*tuple(sys.argv[1:]))
