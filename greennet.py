import os
import sys
import select
import errno
import heapq
import time
import socket
from itertools import chain
from collections import deque, defaultdict

from py.magic import greenlet


READ = 1
WRITE = 2
EXC = 4


class Timeout(Exception):
    pass


class Wait(object):
    __slots__ = ('task', 'expires')
    
    def __init__(self, task, expires):
        self.task = task
        self.expires = expires
    
    def timeout(self):
        self.task.throw(Timeout)
    
    def __cmp__(self, other):
        return cmp(self.expires, other.expires)


class Sleep(Wait):
    __slots__ = ()
    
    def timeout(self):
        self.task.switch()


class FDWait(Wait):
    __slots__ = ('fd', 'mask')
    
    def __init__(self, task, fd, read=False,
                 write=False, exc=False, expires=None):
        super(FDWait, self).__init__(task, expires)
        self.fd = fd
        self.mask = (read and READ) | (write and WRITE) | (exc and EXC)
    
    def fileno(self):
        return self.fd


class Hub(object):
    def __init__(self):
        self.greenlet = greenlet(self._run)
        self.fdwaits = []
        self.timeouts = []
        self.tasks = deque()
    
    def poll(self, fd, read=False, write=False, exc=False, timeout=None):
        expires = None if timeout is None else time.time() + timeout
        if hasattr(fd, 'fileno'):
            fd = fd.fileno()
        wait = FDWait(greenlet.getcurrent(), fd, read, write, exc, expires)
        self.fdwaits.append(wait)
        if timeout is not None:
            self._add_timeout(wait)
        self.greenlet.switch()
    
    def sleep(self, timeout):
        expires = time.time() + timeout
        sleep = Sleep(greenlet.getcurrent(), expires)
        self._add_timeout(sleep)
        self.greenlet.switch()
    
    def schedule(self, task, *args, **kwargs):
        try:
            task.parent = self.greenlet
        except ValueError:
            pass
        self.tasks.append((task, args, kwargs))
    
    def switch(self):
        self.schedule(greenlet.getcurrent())
        self.greenlet.switch()
    
    def run(self):
        self.greenlet.switch()
    
    def _run_tasks(self):
        for _ in xrange(len(self.tasks)):
            task, args, kwargs = self.tasks.popleft()
            task.switch(*args, **kwargs)
    
    def _add_timeout(self, item):
        heapq.heappush(self.timeouts, item)
    
    def _remove_timeout(self, item):
        self.timeouts.remove(item)
        heapq.heapify(self.timeouts)
    
    def _handle_timeouts(self):
        while self.timeouts:
            wait = self.timeouts[0]
            timeout = wait.expires - time.time()
            if timeout <= 0.0:
                heapq.heappop(self.timeouts)
                if isinstance(wait, FDWait):
                    self.fdwaits.remove(wait)
                wait.timeout()
            else:
                return timeout
    
    def _run(self):
        while self.fdwaits or self.tasks or self.timeouts:
            self._run_tasks()
            if self.fdwaits:
                r = []; w = []; e = []
                for wait in self.fdwaits:
                    if wait.mask & READ:
                        r.append(wait)
                    if wait.mask & WRITE:
                        w.append(wait)
                    if wait.mask & EXC:
                        e.append(wait)
                while True:
                    timeout = self._handle_timeouts()
                    try:
                        r, w, e = select.select(r, w, e, timeout)
                    except (select.error, IOError, OSError), e:
                        if e.args[0] == errno.EINTR:
                            continue
                        raise
                    break
                for wait in chain(r, w, e):
                    self.fdwaits.remove(wait)
                    if wait.expires is not None:
                        self._remove_timeout(wait)
                    wait.task.switch()
            elif self.timeouts:
                timeout = self._handle_timeouts()
                if timeout is not None:
                    time.sleep(timeout)


_hub = None
def get_hub():
    global _hub
    if _hub is None:
        _hub = Hub()
    return _hub


def schedule(task, *args, **kwargs):
    get_hub().schedule(task, *args, **kwargs)


def switch():
    get_hub().switch()


def run():
    get_hub().run()


def sleep(timeout):
    get_hub().sleep(timeout)


def readable(obj, timeout=None):
    get_hub().poll(obj, read=True, timeout=timeout)


def writeable(obj, timeout=None):
    get_hub().poll(obj, write=True, timeout=timeout)


def accept(sock, timeout=None):
    readable(sock, timeout=timeout)
    return sock.accept()


def send(sock, data, timeout=None):
    writeable(sock, timeout=timeout)
    return sock.send(data)


def sendall(sock, data, timeout=None):
    if timeout is not None:
        end = time.time() + timeout
    while data:
        data = data[send(sock, data, timeout):]
        if timeout is not None:
            timeout = end - time.time()


def recv(sock, bufsize, flags=0, timeout=None):
    readable(sock, timeout=timeout)
    return sock.recv(bufsize, flags)


def connect(sock, addr, timeout=None):
    sock_timeout = sock.gettimeout()
    if sock_timeout != 0.0:
        sock.setblocking(False)
    try:
        while True:
            try:
                sock.connect(addr)
                return
            except socket.error, err:
                if ((err.args[0] == errno.EINPROGRESS) or
                    ((sys.platform == 'win32') and
                     (err.args[0] == errno.WSAEWOULDBLOCK))):
                    break
                elif err.args[0] != errno.EINTR:
                    raise
        if sys.platform == 'win32':
            get_hub().poll(sock, write=True, exc=True, timeout=timeout)
        else:
            writeable(sock, timeout=timeout)
        err = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if err != 0:
            raise socket.error(err, os.strerror(err))
    finally:
        if sock_timeout != 0.0:
            sock.settimeout(sock_timeout)

