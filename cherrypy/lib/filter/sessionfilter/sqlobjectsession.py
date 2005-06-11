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
from basesession import BaseSession
import cherrypy.cpg

from sessionerrors import *

from sqlobject import *
from basesessiondict import BaseSessionDict

class SQLObjectSessionDict(BaseSessionDict):
    def __init__(self, sqlObject):
        self.__sqlObject = sqlObject
        self.threadCount = 0
    
    def __attrSub(self, attr):
        return { 
                 'key': 'session_key', \
                 'lastAccess' : 'last_access'

               }.get(attr, attr)
        
    def __getattr__(self, attr):
        if attr in ['timestamp', 'timeout', 'lastAccess', 'key']:
            return getattr(self.__sqlObject, self.__attrSub(attr))

    def __setattr__(self, attr, value):
        if attr == 'key' or attr == 'timestamp':
            raise SessionImmutableError
        else:
            object.__setattr__(self, self.__attrSub(attr), value)

    def __getitem__(self, key):
        # make shure it is not an attribute
        if key in ['timestamp', 'timeout', 'lastAccess', 'key']:
            raise KeyError
        try:
            return getattr(self.__sqlObject, key)
        except AttributeError:
            raise KeyError

    def __setitem__(self, key, value):
        # make shure it is not an attribute
        if key in ['timestamp', 'timeout', 'lastAccess', 'key']:
            raise KeyError
        try:
            return setattr(self.__sqlObject, key, value)
        except AttributeError:
            return KeyError

    def __str__(self):
        return str(self.__sqlObject)
      
class SQLObjectSession(BaseSession):
    
    def __init__(self, sessionName):
        BaseSession.__init__(self, sessionName)
        
        dbClassName = cherrypy.cpg.config.get('%s.dbClassName' % sessionName)
        self.Session = cherrypy._cputil.getSpecialAttribute(dbClassName)
    
    def newSession(self):
        """ Return a new sessionMap instance """
        
        newSession = self.Session(session_key = self.generateSessionKey())
        return SQLObjectSessionDict(newSession)
        
        
    def getSession(self, sessionKey):
        resultList = list(self.Session.select(self.Session.q.session_key == sessionKey))
        
        if resultList:
            return SQLObjectSessionDict(resultList[0])
        else:
            raise SessionNotFoundError
    
    def setSession(self, sessionData):
        # all changes are automatically commited so
        pass
        
    def delSession(self, sessionKey):
        # figure out what to catch when this doesn't work
        Session.delete(Session.q.session_key=='abcd')
        
        #raise SessionNotFoundError
    
    def cleanUpOldSessions(self):
        # running a single query would be a huge performace boost
        for sessionKey in __data:
            session = sessionData[sessionKey]
            if session.expired():
                self.delSession(sessionKey)

'''
Session.createTable()
p = Session(session_key = 'abcd', timestamp = 330, count = 123)
Session.delete(Session.q.session_key=='abcd')

smanage = SQLObjectSession('test')
print smanage.getSession('abcd')
'''
