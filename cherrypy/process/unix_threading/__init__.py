import threading
from unix_threading import _pthread_cond

class NativeEvent(threading._Event):
    def __init__(self):
        threading._Event.__init__(self)
        self.__cond = _pthread_cond.Condition()

