"""SSL functionality."""


from __future__ import with_statement
from contextlib import closing
import time
import socket

from OpenSSL import SSL, crypto

import greennet
from greennet import greenlet


class peekable(object):
    
    """Wrapper to add support for MSG_PEEK to SSL.Connection objects."""
    
    def __init__(self, connection):
        self._con = connection
        self.__buf = ''
    
    def pending(self):
        return len(self.__buf) + self._con.pending()
    
    def recv(self, bufsize, flags=0):
        if flags not in (0, socket.MSG_PEEK):
            raise ValueError('only acceptable flag is MSG_PEEK')
        needed = bufsize - len(self.__buf)
        if needed > 0:
            if flags & socket.MSG_PEEK:
                self.__buf += self._con.recv(needed)
                data = self.__buf
            else:
                data = self.__buf + self._con.recv(needed)
                self.__buf = ''
        elif needed == 0:
            data = self.__buf
            if not flags & socket.MSG_PEEK:
                self.__buf = ''
        else:
            data = self.__buf[:bufsize]
            if not flags & socket.MSG_PEEK:
                self.__buf = self.__buf[bufsize:]
        return data
    
    def __getattr__(self, name):
        return getattr(self._con, name)


def _setup_connection(sock, cert, verify):
    """Wrap a socket in SSL.Connection and peekable objects."""
    ctx = SSL.Context(SSL.SSLv23_METHOD)
    ctx.set_options(SSL.OP_NO_SSLv2)
    ctx.set_options(SSL.OP_SINGLE_DH_USE)
    ctx.set_options(SSL.OP_ALL)
    if cert is not None:
        ctx.use_certificate_file(cert['certfile'])
        ctx.use_privatekey_file(cert['keyfile'])
        ctx.check_privatekey()
    if verify is not None:
        ctx.load_verify_locations(verify['cafile'])
        ctx.set_verify(verify['mode'], verify['callback'])
        ctx.set_verify_depth(verify.get('depth', 1))
    sock = peekable(SSL.Connection(ctx, sock))
    sock.setblocking(False)
    return sock


def _io(op, sock, args=(), kw=None, timeout=None):
    """Perform an operation, handling SSL error conditions."""
    if kw is None:
        kw = {}
    if timeout is None:
        timeout = kw.pop('timeout', None)
    if timeout is not None:
        end = time.time() + timeout
        kw['timeout'] = timeout
    while True:
        try:
            return op(sock, *args, **kw)
        except SSL.ZeroReturnError:
            return ''
        except SSL.WantReadError:
            greennet.readable(sock, kw.get('timeout'))
        except SSL.WantWriteError:
            greennet.writable(sock, kw.get('timeout'))
        if timeout is not None:
            kw['timeout'] = end - time.time()


def connect(sock, address=None, cert=None, verify=None, timeout=None):
    """Connect using SSL.
    
    If address is None or not specified, sock is expected to be a connected
    regular socket. If address is specified, sock must be unconnected, and
    will be connected to the specified address. This function starts client-
    side SSL (using set_connect_state).
    
    The calling task will be suspended until the socket is connected and the
    SSL handshake is complete.
    """
    if address is not None:
        if timeout is not None:
            end = time.time() + timeout
        greennet.connect(sock, address, timeout)
        if timeout is not None:
            timeout = end - time.time()
    sock = _setup_connection(sock, cert, verify)
    sock.set_connect_state()
    _io(lambda sock: sock.do_handshake(), sock, timeout=timeout)
    return sock


def accept(sock, cert=None, verify=None, timeout=None):
    """Accept an SSL connection.
    
    The sock argument is an already connected socket-like object. This
    function starts server-side SSL (using set_accept_state).
    
    The calling task will be suspended until the SSL handshake is complete.
    """
    sock = _setup_connection(sock, cert, verify)
    sock.set_accept_state()
    _io(lambda sock: sock.do_handshake(), sock, timeout=timeout)
    return sock


def peekablepair(cert1, cert2):
    """Return a pair of connected peekable SSL connections."""
    s1, s2 = socket.socketpair()
    s1 = _setup_connection(s1, cert1, None)
    s2 = _setup_connection(s2, cert2, None)
    s1.set_accept_state()
    s2.set_connect_state()
    socks = [s1, s2]
    handshaking = [True, True]
    while any(handshaking):
        for i, h in enumerate(handshaking):
            if not h:
                continue
            try:
                socks[i].do_handshake()
                handshaking[i] = False
            except SSL.WantReadError:
                pass
            except SSL.WantWriteError:
                pass
    return s1, s2


def shutdown(sock, timeout=None):
    """Shut down SSL.
    
    Calls the SSL shutdown method until it completes. The calling task will be
    suspended until this completes.
    """
    if timeout is not None:
        end = time.time() + timeout
    h = greennet.get_hub()
    while not sock.shutdown():
        h.poll(sock, read=sock.want_read(),
               write=sock.want_write(), timeout=timeout)
        if timeout is not None:
            timeout = end - time.time()


def renegotiate_client(sock, cert=None, verify=None, timeout=None):
    """Renegotiate the SSL connection (client-side).
    
    Specify new certificates and verification options, and re-handshake. The
    calling task will be suspended until the re-handshake is complete.
    """
    ctx = sock.get_context()
    if cert is not None:
        ctx.use_certificate_file(cert['certfile'])
        ctx.use_privatekey_file(cert['keyfile'])
        ctx.check_privatekey()
    if verify is not None:
        ctx.load_verify_locations(verify['cafile'])
        ctx.set_verify(verify['mode'], verify['callback'])
        ctx.set_verify_depth(verify.get('depth', 1))
    sock.renegotiate()
    _io(lambda sock: sock.do_handshake(), sock, timeout=timeout)


def renegotiate_server(sock, cert=None, verify=None, timeout=None):
    """Renegotiate the SSL connection (server-side).
    
    Specify new certificates and verification options, and re-handshake. The
    calling task will be suspended until the re-handshake is complete.
    """
    if timeout is not None:
        end = time.time() + timeout
    shutdown(sock, timeout)
    if timeout is not None:
        timeout = end - time.time()
    sock = sock.dup()
    sock = _setup_connection(sock, cert, verify)
    sock.set_accept_state()
    _io(lambda sock: sock.do_handshake(), sock, timeout=timeout)
    return sock


def recv(sock, bufsize, flags=0, timeout=None):
    """Receive some data from the given SSL connection."""
    pending = sock.pending()
    if pending:
        args = (min(bufsize, pending),)
    else:
        args = (bufsize,)
    if flags:
        args += (flags,)
    if pending and not flags:
        return sock.recv(*args)
    return _io(greennet.recv, sock, args, timeout=timeout)


def send(sock, data, timeout=None):
    """Send some data on the given SSL connection."""
    return _io(greennet.send, sock, (data,), timeout=timeout)

