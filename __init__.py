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
Global module that all modules developing with CherryPy should import.
"""

__version__ = '2.1.0 alpha'

from _cperror import *

import config
import server

# Use a flag to indicate the state of the cherrypy application server.
# 0 = Not started
# None = In process of starting
# 1 = Started, ready to receive requests
_appserver_state = 0
_httpserver = None

try:
    from threading import local
except ImportError:
    from cherrypy._cpthreadinglocal import local

# Create request and response object (the same objects will be used
#   throughout the entire life of the webserver)
request = local()
response = local()

# Create threadData object as a thread-specific all-purpose storage
threadData = local()

# decorator function for exposing methods
def expose(func):
    func.exposed = True
    return func

def log(msg, context='', severity=0):
    """Syntactic sugar for writing to the log."""
    import _cputil
    logfunc = _cputil.getSpecialAttribute('_cpLogMessage')
    logfunc(msg, context, severity)

