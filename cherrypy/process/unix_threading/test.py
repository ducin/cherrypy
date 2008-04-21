#! /usr/bin/env python
import select
import sys
import os
import threading
from _native_event import NativeEvent
import time

"""
def test(event_class):
    events = []
    def wait_thread():
        e = event_class()
        events.append(e)
        for i in range(100):
            e.wait()
    threads = []
    for _ in range(100):
        t = threading.Thread(target=wait_thread)
        t.start()
        threads.append(t)
    time.sleep(1)
    for i in range(100):
        for e in events:
            e.set()
            e.clear()
    for t in threads:
        t.join()

if __name__ == '__main__':
    if eval(sys.argv[1]) == 0:
        test(threading.Event)
    else:
        test(unix_threading.NativeEvent)
"""
import unix_threading._pthread_cond
print unix_threading._pthread_cond.__file__
print os.getpid()
def test():
    ev = NativeEvent()
    def proc():
        time.sleep(10)
        ev.set()

    t = threading.Thread(target=proc)
    t.start()
    
    try:
        ev.wait()
    except KeyboardInterrupt:
        print 'hi'

test()


