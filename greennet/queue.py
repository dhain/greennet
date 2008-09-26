import time
from collections import deque

from py.magic import greenlet

from greennet import get_hub
from greennet.hub import Wait


class QueueWait(Wait):
    __slots__ = ('queue',)
    
    def __init__(self, task, queue, expires):
        super(QueueWait, self).__init__(task, expires)
        self.queue = queue
    
    def timeout(self):
        getattr(self.queue, self._wait_attr).remove(self)
        super(QueueWait, self).timeout()

class PopWait(QueueWait):
    """Wait for a pop to happen."""
    __slots__ = ()
    _wait_attr = '_pop_waits'

class AppendWait(QueueWait):
    """Wait for an append to happen."""
    __slots__ = ()
    _wait_attr = '_append_waits'


class Queue(object):
    def __init__(self, maxlen=None, hub=None):
        self.queue = deque()
        self.maxlen = maxlen
        self.hub = get_hub() if hub is None else hub
        self._append_waits = deque()
        self._pop_waits = deque()
    
    def __len__(self):
        return len(self.queue)
    
    def full(self):
        if self.maxlen is None:
            return False
        return len(self.queue) >= self.maxlen
    
    def _wait_for_append(self, timeout):
        expires = None if timeout is None else time.time() + timeout
        wait = AppendWait(greenlet.getcurrent(), self, expires)
        if timeout is not None:
            self.hub._add_timeout(wait)
        self._append_waits.append(wait)
        self.hub.run()
    
    def _wait_for_pop(self, timeout):
        expires = None if timeout is None else time.time() + timeout
        wait = PopWait(greenlet.getcurrent(), self, expires)
        if timeout is not None:
            self.hub._add_timeout(wait)
        self._pop_waits.append(wait)
        self.hub.run()
    
    def _popped(self):
        if self._pop_waits:
            wait = self._pop_waits.popleft()
            if wait.expires is not None:
                self.hub._remove_timeout(wait)
            self.hub.schedule(wait.task)
    
    def _appended(self):
        if self._append_waits:
            wait = self._append_waits.popleft()
            if wait.expires is not None:
                self.hub._remove_timeout(wait)
            self.hub.schedule(wait.task)
    
    def wait_until_empty(self, timeout=None):
        if not self.queue:
            return
        expires = None if timeout is None else time.time() + timeout
        wait = PopWait(greenlet.getcurrent(), self, expires)
        if timeout is not None:
            self.hub._add_timeout(wait)
        while self.queue:
            self._pop_waits.append(wait)
            self.hub.run()
        self._popped()
    
    def pop(self, timeout=None):
        if not self.queue:
            self._wait_for_append(timeout)
        item = self.queue.pop()
        self._popped()
        return item
    
    def popleft(self, timeout=None):
        if not self.queue:
            self._wait_for_append(timeout)
        item = self.queue.popleft()
        self._popped()
        return item
    
    def clear(self):
        self.queue.clear()
        self._popped()
    
    def append(self, item, timeout=None):
        if self.full():
            self._wait_for_pop(timeout)
        self.queue.append(item)
        self._appended()
    
    def appendleft(self, item, timeout=None):
        if self.full():
            self._wait_for_pop(timeout)
        self.queue.appendleft(item)
        self._appended()

