import os
import sys
import time
import socket

from py.magic import greenlet

from greennet.hub import Hub, Timeout
from greennet.util import prefixes

try:
    from greennet import ssl
except ImportError:
    ssl = None


class ConnectionLost(Exception):
    pass


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


def recv_bytes(sock, n, bufsize=None, timeout=None):
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
            data = _recv(sock, test + len(term))
            yield data
            break
        for p in prefixes(term):
            if data.endswith(p):
                seen = len(data) - len(p)
                if seen:
                    data = _recv(sock, seen)
                    yield data
                break
        else:
            data = _recv(sock, len(data))
            yield data
        if timeout is not None:
            timeout = end - time.time()


def recv_until_maxlen(sock, term, maxlen, exc_type,
                      bufsize=None, timeout=None):
    ret = ''
    for data in recv_until(sock, term, bufsize, timeout):
        ret += data
        if len(ret) > maxlen:
            raise exc()
    return ret

