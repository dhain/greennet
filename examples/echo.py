from __future__ import with_statement
from contextlib import closing
import socket

from py.magic import greenlet

import greennet


def echo(sock):
    with closing(sock):
        bufsize = sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
        while True:
            data = greennet.recv(sock, bufsize)
            if not data:
                break
            greennet.sendall(sock, data)


if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', 1234))
    sock.listen(socket.SOMAXCONN)
    with closing(sock):
        while True:
            client, addr = greennet.accept(sock)
            greennet.schedule(greenlet(echo), client)

