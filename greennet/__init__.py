import os
import sys
import time
import errno
import socket

from py.magic import greenlet

from greennet.hub import Hub, Timeout
from greennet.util import prefixes

try:
    from greennet import ssl
except ImportError:
    ssl = None


class ConnectionLost(Exception):
    """Connection was terminated."""
    pass


try:
    import threading
    _hubs = threading.local()
    def get_hub():
        """Return the Hub instance for this thread."""
        global _hubs
        try:
            return _hubs.hub
        except AttributeError:
            _hubs.hub = Hub()
            return _hubs.hub
except ImportError:
    _hub = None
    def get_hub():
        """Return the global Hub instance."""
        global _hub
        if _hub is None:
            _hub = Hub()
        return _hub


def schedule(task, *args, **kwargs):
    """Schedule a task to be run during the next iteration of the loop."""
    get_hub().schedule(task, *args, **kwargs)


def switch():
    """Reschedule the current task, and run the event-loop."""
    get_hub().switch()


def run():
    """Run the event loop.
    
    This will only return when there is nothing more scheduled to run.
    """
    get_hub().run()


def sleep(timeout):
    """Suspend the current task for the specified number of seconds."""
    get_hub().sleep(timeout)


def call_later(task, timeout, *args, **kwargs):
    """Run the task after the specified number of seconds."""
    get_hub().call_later(task, timeout, *args, **kwargs)


def readable(obj, timeout=None):
    """Suspend the current task until the selectable-object is readable."""
    get_hub().poll(obj, read=True, timeout=timeout)


def writeable(obj, timeout=None):
    """Suspend the current task until the selectable-object is writable."""
    get_hub().poll(obj, write=True, timeout=timeout)


def connect(sock, addr, timeout=None):
    """Connect a socket to the specified address.
    
    Suspends the current task until the connection is established.
    
    >>> import socket
    >>> s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    >>> s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    >>> s2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    >>> s2.bind(('127.0.0.1', 12345))
    >>> s2.listen(1)
    >>> connect(s1, ('127.0.0.1', 12345))
    >>> s3 = s2.accept()[0]
    >>> s1.send('some data')
    9
    >>> s3.recv(9)
    'some data'
    >>> s3.close()
    >>> s1.close()
    >>> s2.close()
    """
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


def accept(sock, timeout=None):
    """Accept a connection on the given socket.
    
    >>> import socket
    >>> s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    >>> s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    >>> s2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    >>> s2.bind(('127.0.0.1', 12345))
    >>> s2.listen(1)
    >>> accept(s2, 0)
    Traceback (most recent call last):
        ...
    Timeout
    >>> connect(s1, ('127.0.0.1', 12345))
    >>> s3 = accept(s2)[0]
    >>> s1.send('some data')
    9
    >>> s3.recv(9)
    'some data'
    >>> s3.close()
    >>> s1.close()
    >>> s2.close()
    """
    readable(sock, timeout=timeout)
    return sock.accept()


def send(sock, data, timeout=None):
    """Send some data on the given socket.
    
    >>> import socket
    >>> s1, s2 = socket.socketpair()
    >>> send(s1, 'some data')
    9
    >>> s2.recv(9)
    'some data'
    >>> s1.close()
    >>> s2.close()
    """
    writeable(sock, timeout=timeout)
    return sock.send(data)


def recv(sock, bufsize, flags=0, timeout=None):
    """Receive some data from the given socket.
    
    >>> import socket
    >>> s1, s2 = socket.socketpair()
    >>> recv(s2, 1, timeout=0)
    Traceback (most recent call last):
        ...
    Timeout
    >>> s1.send('some data')
    9
    >>> recv(s2, 4, socket.MSG_PEEK)
    'some'
    >>> recv(s2, 9)
    'some data'
    >>> s1.close()
    >>> s2.close()
    """
    readable(sock, timeout=timeout)
    return sock.recv(bufsize, flags)


def sendall(sock, data, timeout=None):
    """Send all data on the given socket.
    
    >>> import socket
    >>> s1, s2 = socket.socketpair()
    >>> sendall(s1, 'some data')
    >>> s2.recv(9)
    'some data'
    >>> s1.close()
    >>> s2.close()
    """
    if ssl and isinstance(sock, ssl.peekable):
        _send = ssl.send
    else:
        _send = send
    if timeout is not None:
        end = time.time() + timeout
    while data:
        data = data[_send(sock, data, timeout):]
        if timeout is not None:
            timeout = end - time.time()


def recv_bytes(sock, n, bufsize=None, timeout=None):
    """Receive specified number of bytes from socket.
    
    Generator yields data as it becomes available.
    
    Raises ConnectionLost if the connection is terminated before the
    specified number of bytes is read.
    
    >>> import socket
    >>> s1, s2 = socket.socketpair()
    >>> list(recv_bytes(s1, 9, timeout=0))
    Traceback (most recent call last):
        ...
    Timeout
    >>> s2.send('some data')
    9
    >>> list(recv_bytes(s1, 9))
    ['some data']
    >>> s2.send('some data')
    9
    >>> list(recv_bytes(s1, 9, 4))
    ['some', ' dat', 'a']
    >>> s1.close()
    >>> s2.close()
    """
    if ssl and isinstance(sock, ssl.peekable):
        _recv = ssl.recv
    else:
        _recv = recv
    if bufsize is None:
        bufsize = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
    if timeout is not None:
        end = time.time() + timeout
    while n:
        data = _recv(sock, min(n, bufsize), timeout=timeout)
        if not data:
            raise ConnectionLost()
        yield data
        n -= len(data)
        if timeout is not None:
            timeout = end - time.time()


def recv_until(sock, term, bufsize=None, timeout=None):
    """Receive from socket until the specified terminator.
    
    Generator yields data as it becomes available.
    
    Raises ConnectionLost if the connection is terminated before the
    terminator is encountered.
    
    >>> import socket
    >>> s1, s2 = socket.socketpair()
    >>> list(recv_until(s1, 'at', timeout=0))
    Traceback (most recent call last):
        ...
    Timeout
    >>> s2.send('some data')
    9
    >>> list(recv_until(s1, 'at'))
    ['some dat']
    >>> s1.recv(1)
    'a'
    >>> s2.send('some data')
    9
    >>> list(recv_until(s1, 'at', 4))
    ['some', ' dat']
    >>> s1.recv(1)
    'a'
    >>> s1.close()
    >>> s2.close()
    """
    if ssl and isinstance(sock, ssl.peekable):
        _recv = ssl.recv
    else:
        _recv = recv
    if bufsize is None:
        bufsize = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
    if timeout is not None:
        end = time.time() + timeout
    assert bufsize >= len(term)
    while True:
        data = _recv(sock, bufsize, socket.MSG_PEEK, timeout=timeout)
        if not data:
            raise ConnectionLost()
        test = data.find(term)
        if test > -1:
            data = sock.recv(test + len(term))
            yield data
            break
        for p in prefixes(term):
            if data.endswith(p):
                seen = len(data) - len(p)
                if seen:
                    data = sock.recv(seen)
                    yield data
                break
        else:
            data = sock.recv(len(data))
            yield data
        if timeout is not None:
            timeout = end - time.time()


def recv_until_maxlen(sock, term, maxlen, exc_type,
                      bufsize=None, timeout=None):
    """Like recv_until, but if the terminator is not encountered within a
    given number of bytes, raises the given exception.
    
    >>> import socket
    >>> s1, s2 = socket.socketpair()
    >>> list(recv_until_maxlen(s1, 'at', 9, RuntimeError, timeout=0))
    Traceback (most recent call last):
        ...
    Timeout
    >>> s2.send('some data')
    9
    >>> list(recv_until_maxlen(s1, 'at', 9, RuntimeError))
    ['some dat']
    >>> s1.recv(1)
    'a'
    >>> s2.send('some data')
    9
    >>> list(recv_until_maxlen(s1, 'at', 9, RuntimeError, 4))
    ['some', ' dat']
    >>> s1.recv(1)
    'a'
    >>> s2.send('some data')
    9
    >>> list(recv_until_maxlen(s1, 'at', 4, RuntimeError))
    Traceback (most recent call last):
        ...
    RuntimeError
    >>> s1.close()
    >>> s2.close()
    """
    sofar = 0
    for data in recv_until(sock, term, bufsize, timeout):
        sofar += len(data)
        if sofar > maxlen:
            raise exc_type()
        yield data

