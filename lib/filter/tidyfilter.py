"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import os, cgi
from basefilter import BaseFilter
from cherrypy import cpg

class TidyFilter(BaseFilter):
    """
    Filter that runs the response through Tidy.
    Note that we use the standalone Tidy tool rather than the python
    mxTidy module. This is because this module doesn't seem to be
    stable and it crashes on some HTML pages (which means that the
    server would also crash)
    """

    def __init__(self, tidyPath, tmpDir, errorsToIgnore = []):
        self.tidyPath = tidyPath
        self.tmpDir = tmpDir
        self.errorsToIgnore = errorsToIgnore

    def beforeResponse(self):
        ct = cpg.response.headerMap.get('Content-Type')
        if ct == 'text/html':
            pageFile = os.path.join(self.tmpDir, 'page.html')
            outFile = os.path.join(self.tmpDir, 'tidy.out')
            errFile = os.path.join(self.tmpDir, 'tidy.err')
            f = open(pageFile, 'wb')
            f.write(cpg.response.body)
            f.close()
            encoding = cpg.response.headerMap.get('Content-Encoding', '')
            if encoding:
                encoding = '-u' + encoding
            os.system('"%s" %s -f %s -o %s %s' % (
                self.tidyPath, encoding, errFile, outFile, pageFile))
            f = open(errFile, 'rb')
            err = f.read()
            f.close()

            errList = err.splitlines()
            newErrList = []
            for err in errList:
                if (err.find('Warning') != -1 or err.find('Error') != -1):
                    ignore = 0
                    for errIgn in self.errorsToIgnore:
                        if err.find(errIgn) != -1:
                            ignore = 1
                            break
                    if not ignore: newErrList.append(err)

            if newErrList:
                oldHtml = cpg.response.body
                cpg.response.body = "Wrong HTML:<br>" + cgi.escape('\n'.join(newErrList)).replace('\n','<br>')
                cpg.response.body += '<br><br>'
                i=0
                for line in oldHtml.splitlines():
                    i += 1
                    cpg.response.body += "%03d - "%i + cgi.escape(line).replace('\t','    ').replace(' ','&nbsp;') + '<br>'

                cpg.response.headerMap['Content-Length'] = len(cpg.response.body)
