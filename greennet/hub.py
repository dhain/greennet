"""Schedule and run tasks based on an event-loop."""


import select
import errno
import heapq
import time
import socket
from itertools import chain
from collections import deque

from greennet import greenlet

READ = 1
WRITE = 2
EXC = 4


class Timeout(Exception):
    """Timed out waiting for an event."""
    pass


class Wait(object):
    
    """Wait for an event."""
    
    __slots__ = ('task', 'expires')
    
    def __init__(self, task, expires):
        self.task = task
        self.expires = expires
    
    def timeout(self):
        """Called when the event times out.
        
        Default implemetation raises Timeout.
        """
        self.task.throw(Timeout)
    
    def __cmp__(self, other):
        """cmp(x, y) <==> cmp(x.expires, y.expires)"""
        return cmp(self.expires, other.expires)


class Sleep(Wait):
    
    """Sleep for the specified timeout, then resume."""
    
    __slots__ = ('args', 'kwargs')
    
    def __init__(self, task, expires, args=(), kwargs={}):
        super(Sleep, self).__init__(task, expires)
        self.args = args
        self.kwargs = kwargs
    
    def timeout(self):
        """Resumes task instead of raising Timeout."""
        self.task.switch(*self.args, **self.kwargs)


class FDWait(Wait):
    
    """Wait for an IO event."""
    
    __slots__ = ('fd', 'mask')
    
    def __init__(self, task, fd, read=False,
                 write=False, exc=False, expires=None):
        super(FDWait, self).__init__(task, expires)
        self.fd = fd
        self.mask = (read and READ) | (write and WRITE) | (exc and EXC)
    
    def fileno(self):
        return self.fd


class Hub(object):
    
    """Schedule and run tasks based on an event-loop.
    
    The default implementation uses select() to wait on FDWaits.
    """
    
    def __init__(self):
        self.greenlet = greenlet(self._run)
        self.fdwaits = set()
        self.timeouts = []
        self.tasks = deque()
    
    def poll(self, fd, read=False, write=False, exc=False, timeout=None):
        """Suspend the current task until an IO event occurs."""
        expires = None if timeout is None else time.time() + timeout
        if hasattr(fd, 'fileno'):
            fd = fd.fileno()
        wait = FDWait(greenlet.getcurrent(), fd, read, write, exc, expires)
        self.fdwaits.add(wait)
        if timeout is not None:
            self._add_timeout(wait)
        self.greenlet.switch()
    
    def sleep(self, timeout):
        """Suspend the current task for the specified number of seconds."""
        expires = time.time() + timeout
        sleep = Sleep(greenlet.getcurrent(), expires)
        self._add_timeout(sleep)
        self.greenlet.switch()
    
    def call_later(self, task, timeout, *args, **kwargs):
        """Run the task after the specified number of seconds."""
        expires = time.time() + timeout
        sleep = Sleep(task, expires, args, kwargs)
        self._add_timeout(sleep)
    
    def schedule(self, task, *args, **kwargs):
        """Schedule a task to be run during the next iteration of the loop."""
        try:
            task.parent = self.greenlet
        except ValueError:
            pass
        self.tasks.append((task, args, kwargs))
    
    def switch(self):
        """Reschedule the current task, and run the event-loop."""
        self.schedule(greenlet.getcurrent())
        self.greenlet.switch()
    
    def run(self):
        """Run the event loop.
        
        This will only return when there is nothing more scheduled to run.
        """
        self.greenlet.switch()
    
    def _run_tasks(self):
        """Run all immediately available tasks.
        
        Returns when all tasks either finish or are waiting for an event.
        """
        while self.tasks:
            task, args, kwargs = self.tasks.popleft()
            task.switch(*args, **kwargs)
    
    def _add_timeout(self, item):
        """Add a Wait object to the timeout heap."""
        assert item not in self.timeouts
        heapq.heappush(self.timeouts, item)
    
    def _remove_timeout(self, item):
        """Remove a Wait object from the timeout heap."""
        self.timeouts.remove(item)
        heapq.heapify(self.timeouts)
    
    def _handle_timeouts(self):
        """Fire timeout events and return the next-expiring timeout.
        
        If there are no more timeouts, returns None.
        """
        while self.timeouts:
            wait = self.timeouts[0]
            timeout = wait.expires - time.time()
            if timeout <= 0.0:
                heapq.heappop(self.timeouts)
                if isinstance(wait, FDWait):
                    self.fdwaits.remove(wait)
                self.schedule(greenlet(wait.timeout))
                self._run_tasks()
            else:
                return timeout
    
    def _run(self):
        """Main event loop.
        
        Runs tasks, then handles FDWaits, then handles timeouts. This
        implementation uses select() to wait for IO, and sleep() if there are
        timeouts but no FDWaits.
        """
        while self.fdwaits or self.tasks or self.timeouts:
            self._run_tasks()
            if self.fdwaits:
                while True:
                    timeout = self._handle_timeouts()
                    r = []; w = []; e = []
                    for wait in self.fdwaits:
                        if wait.mask & READ:
                            r.append(wait)
                        if wait.mask & WRITE:
                            w.append(wait)
                        if wait.mask & EXC:
                            e.append(wait)
                    try:
                        r, w, e = select.select(r, w, e, timeout)
                    except (select.error, IOError, OSError), err:
                        if err.args[0] == errno.EINTR:
                            continue
                        raise
                    break
                for wait in chain(r, w, e):
                    self.fdwaits.remove(wait)
                    if wait.expires is not None:
                        self._remove_timeout(wait)
                    self.schedule(wait.task)
            elif self.timeouts:
                timeout = self._handle_timeouts()
                if timeout is not None:
                    time.sleep(timeout)

