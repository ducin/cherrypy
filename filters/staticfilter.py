import os
import urllib

import cherrypy
from cherrypy.lib import cptools
from cherrypy.filters.basefilter import BaseFilter


class StaticFilter(BaseFilter):
    """Filter that handles static content."""
    
    def before_main(self):
        config = cherrypy.config
        if not config.get('static_filter.on', False):
            return
        
        request = cherrypy.request
        path = request.object_path
        
        regex = config.get('static_filter.match', '')
        if regex:
            import re
            if not re.search(regex, path):
                return
        
        filename = config.get('static_filter.file')
        if not filename:
            staticDir = config.get('static_filter.dir')
            if not staticDir:
                msg = ("StaticFilter requires either static_filter.file "
                       "or static_filter.dir (%s)" % request.path)
                raise cherrypy.WrongConfigValue(msg)
            section = config.get('static_filter.dir', return_section=True)
            if section == 'global':
                section = "/"
            section = section.rstrip(r"\/")
            extraPath = path[len(section) + 1:]
            extraPath = extraPath.lstrip(r"\/")
            extraPath = urllib.unquote(extraPath)
            # If extraPath is "", filename will end in a slash
            filename = os.path.join(staticDir, extraPath)
        
        # If filename is relative, make absolute using "root".
        # Note that, if "root" isn't defined, we still may send
        # a relative path to serveFile.
        if not os.path.isabs(filename):
            root = config.get('static_filter.root', '').rstrip(r"\/")
            if root:
                filename = os.path.join(root, filename)
        
        try:
            cptools.serveFile(filename)
            request.execute_main = False
        except cherrypy.NotFound:
            # If we didn't find the static file, continue handling the
            # request. We might find a dynamic handler instead.
            
            # But first check for an index file if a folder was requested.
            if filename[-1:] in ("/", "\\"):
                idx = config.get('static_filter.index', '')
                if idx:
                    try:
                        cptools.serveFile(os.path.join(filename, idx))
                        request.execute_main = False
                    except cherrypy.NotFound:
                        pass
