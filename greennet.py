import os
import sys
import select
import errno
import heapq
import time
import socket
from collections import deque, defaultdict

from py.magic import greenlet


class Timeout(Exception):
    pass


class Hub(object):
    def __init__(self):
        self.greenlet = greenlet(self._run)
        self.readers = defaultdict(deque)
        self.writers = defaultdict(deque)
        self.excs = defaultdict(deque)
        self.timeouts = []
        self.tasks = deque()
    
    def poll(self, fd, read=False, write=False, exc=False, timeout=None):
        if hasattr(fd, 'fileno'):
            fd = fd.fileno()
        g = greenlet.getcurrent()
        if read:
            self.readers[fd].append(g)
        if write:
            self.writers[fd].append(g)
        if exc:
            self.excs[fd].append(g)
        if timeout is not None:
            heapq.heappush(self.timeouts, (time.time() + timeout, fd, g))
        self.greenlet.switch()
    
    def schedule(self, task, *args, **kwargs):
        task.parent = self.greenlet
        self.tasks.append((task, args, kwargs))
    
    def switch(self):
        self.schedule(greenlet.getcurrent())
        self.greenlet.switch()
    
    def _remove_wait(self, fd, g):
        if fd in self.readers:
            if len(self.readers[fd]) < 2:
                del self.readers[fd]
            else:
                self.readers[fd].remove(g)
        if fd in self.writers:
            if len(self.writers[fd]) < 2:
                del self.writers[fd]
            else:
                self.writers[fd].remove(g)
        if fd in self.excs:
            if len(self.excs[fd]) < 2:
                del self.excs[fd]
            else:
                self.excs[fd].remove(g)
    
    def _run_tasks(self):
        for _ in xrange(len(self.tasks)):
            task, args, kwargs = self.tasks.popleft()
            task.switch(*args, **kwargs)
    
    def _handle_timeouts(self):
        while self.timeouts:
            timeout, fd, g = self.timeouts[0]
            timeout -= time.time()
            if timeout <= 0.0:
                heapq.heappop(self.timeouts)
                self._remove_wait(fd, g)
                g.throw(Timeout)
            else:
                return timeout
    
    def _run(self):
        while self.readers or self.writers or self.excs or self.tasks:
            self._run_tasks()
            args = [self.readers.keys(),
                    self.writers.keys(),
                    self.excs.keys()]
            while True:
                timeout = self._handle_timeouts()
                if timeout is not None:
                    args.append(timeout)
                try:
                    r, w, e = select.select(*args)
                except select.error, e:
                    if e.args[0] == errno.EINTR:
                        continue
                    raise
                break
            for fd in r:
                for g in self.readers.pop(fd):
                    self._remove_wait(fd, g)
                    g.switch()
            for fd in w:
                for g in self.writers.pop(fd):
                    self._remove_wait(fd, g)
                    g.switch()
            for fd in e:
                for g in self.excs.pop(fd):
                    self._remove_wait(fd, g)
                    g.switch()


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

