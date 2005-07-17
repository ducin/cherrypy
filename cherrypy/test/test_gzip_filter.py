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

import gzip, StringIO
import cherrypy

class Root:
    def index(self):
        yield "Hello, world"
    index.exposed = True
    
    def noshow(self):
        # Test for ticket #147, where yield showed no exceptions (content-
        # encoding was still gzip even though traceback wasn't zipped).
        raise IndexError
        yield "Here be dragons"
    noshow.exposed = True

cherrypy.root = Root()
cherrypy.config.update({
    'global': {
        'server.logToScreen': False,
        'server.environment': 'production',
        'gzipFilter.on': True,
    }
})


import helper

europoundUtf8 = u'\x80\xa3'.encode('utf-8')

class GzipFilterTest(helper.CPWebCase):
    
    def testGzipFilter(self):
        zbuf = StringIO.StringIO()
        zfile = gzip.GzipFile(mode='wb', fileobj=zbuf, compresslevel=9)
        zfile.write("Hello, world")
        zfile.close()
        
        self.getPage('/', headers=[("Accept-Encoding", "gzip")])
        self.assertInBody(zbuf.getvalue()[:3])
        
        # Test for ticket #147
        helper.webtest.ignored_exceptions.append(IndexError)
        try:
            self.getPage('/noshow', headers=[("Accept-Encoding", "gzip")])
            self.assert_('Content-Encoding' not in dict(self.headers))
            self.assert_(self.body.endswith("IndexError\n"))
        finally:
            helper.webtest.ignored_exceptions.pop()


if __name__ == "__main__":
    helper.testmain()
