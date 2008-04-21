from unix_threading import NativeEvent
from cherrypy.process import wspbus

class UnixBus(wspbus.Bus):
    def __init__(self):
        self.events = {}
        wspbus.Bus.__init__(self)

    def _get_state_event(self, state):
        try:
            return self.events[state]
        except KeyError:
            event = NativeEvent()
            self.events[state] = event
            return event
    
    def _get_state(self):
        return self._state
    def _set_state(self, value):
        self._state = value
        event = self._get_state_event(value)
        event.set()
        event.clear()
    state = property(_get_state, _set_state)
    
    def wait(self, state, interval=0.1):
        # Don't wait for an event that beat us to the punch ;)
        if self.state != state:
            event = self._get_state_event(state)
            event.wait()

