"""A double-ended queue with an optional maximum size."""


import time
from collections import deque

from greennet import greenlet
from greennet import get_hub
from greennet.hub import Wait


class QueueWait(Wait):
    
    """Abstract class to wait for a Queue event."""
    
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
    
    """A double-ended queue with an optional maximum size.
    
    Tasks will be suspended when they try to pop from an empty Queue or
    append to a full Queue until the operation can complete.
    """
    
    def __init__(self, maxlen=None, hub=None):
        self.queue = deque()
        self.maxlen = maxlen
        self.hub = get_hub() if hub is None else hub
        self._append_waits = deque()
        self._pop_waits = deque()
    
    def __len__(self):
        """len(q) <==> q.__len__()
        
        >>> q = Queue()
        >>> len(q)
        0
        >>> q.append('an item')
        >>> len(q)
        1
        """
        return len(self.queue)
    
    def full(self):
        """Returns True if the Queue is full, else False.
        
        >>> q = Queue(1)
        >>> q.full()
        False
        >>> q.append('an item')
        >>> q.full()
        True
        >>> q.pop()
        'an item'
        >>> q.full()
        False
        """
        if self.maxlen is None:
            return False
        return len(self.queue) >= self.maxlen
    
    def _wait_for_append(self, timeout):
        """Suspend the current task until an append happens.
        
        Call this if popping from an empty Queue.
        """
        expires = None if timeout is None else time.time() + timeout
        wait = AppendWait(greenlet.getcurrent(), self, expires)
        if timeout is not None:
            self.hub._add_timeout(wait)
        self._append_waits.append(wait)
        self.hub.run()
    
    def _wait_for_pop(self, timeout):
        """Suspend the current task until a pop happens.
        
        Call this if appending to a full Queue.
        """
        expires = None if timeout is None else time.time() + timeout
        wait = PopWait(greenlet.getcurrent(), self, expires)
        if timeout is not None:
            self.hub._add_timeout(wait)
        self._pop_waits.append(wait)
        self.hub.run()
    
    def _popped(self):
        """Called when the Queue is reduced in size."""
        if self._pop_waits:
            wait = self._pop_waits.popleft()
            if wait.expires is not None:
                self.hub._remove_timeout(wait)
            self.hub.schedule(wait.task)
    
    def _appended(self):
        """Called when the Queue increases in size."""
        if self._append_waits:
            wait = self._append_waits.popleft()
            if wait.expires is not None:
                self.hub._remove_timeout(wait)
            self.hub.schedule(wait.task)
    
    def wait_until_empty(self, timeout=None):
        """Suspend the current task until the Queue is empty.
        
        >>> q = Queue()
        >>> q.wait_until_empty()
        >>> q.append('an item')
        >>> q.wait_until_empty(0)
        Traceback (most recent call last):
            ...
        Timeout
        """
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
        """Pop an item from the right side of the Queue.
        
        >>> q = Queue()
        >>> q.append('an item')
        >>> q.append('another item')
        >>> q.pop()
        'another item'
        >>> q.pop()
        'an item'
        >>> q.pop(0)
        Traceback (most recent call last):
            ...
        Timeout
        """
        if not self.queue:
            self._wait_for_append(timeout)
        item = self.queue.pop()
        self._popped()
        return item
    
    def popleft(self, timeout=None):
        """Pop an item from the left side of the Queue.
        
        >>> q = Queue()
        >>> q.append('an item')
        >>> q.append('another item')
        >>> q.popleft()
        'an item'
        >>> q.popleft()
        'another item'
        >>> q.popleft(0)
        Traceback (most recent call last):
            ...
        Timeout
        """
        if not self.queue:
            self._wait_for_append(timeout)
        item = self.queue.popleft()
        self._popped()
        return item
    
    def clear(self):
        """Remove all items from the Queue.
        
        >>> q = Queue()
        >>> q.append('an item')
        >>> len(q)
        1
        >>> q.clear()
        >>> len(q)
        0
        """
        self.queue.clear()
        self._popped()
    
    def append(self, item, timeout=None):
        """Append an item to the right side of the Queue.
        
        >>> q = Queue(2)
        >>> q.append('an item')
        >>> len(q)
        1
        >>> q.append('another item')
        >>> len(q)
        2
        >>> q.append('a third item', 0)
        Traceback (most recent call last):
            ...
        Timeout
        >>> len(q)
        2
        >>> q.popleft()
        'an item'
        >>> q.popleft()
        'another item'
        """
        if self.full():
            self._wait_for_pop(timeout)
        self.queue.append(item)
        self._appended()
    
    def appendleft(self, item, timeout=None):
        """Append an item to the left side of the Queue.
        
        >>> q = Queue(2)
        >>> q.appendleft('an item')
        >>> len(q)
        1
        >>> q.appendleft('another item')
        >>> len(q)
        2
        >>> q.appendleft('a third item', 0)
        Traceback (most recent call last):
            ...
        Timeout
        >>> len(q)
        2
        >>> q.popleft()
        'another item'
        >>> q.popleft()
        'an item'
        """
        if self.full():
            self._wait_for_pop(timeout)
        self.queue.appendleft(item)
        self._appended()


if __name__ == '__main__':
    import doctest
    doctest.testmod()
