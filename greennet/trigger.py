"""A thread-safe way to interrupt a Hub waiting on IO."""


import os
import errno

from greennet import get_hub


class Trigger(object):
    
    __slots__ = ('hub', '_gun', '_trigger', '_closed')
    
    def __init__(self, hub=None):
        self.hub = get_hub() if hub is None else hub
        self._gun, self._trigger = os.pipe()
        self._closed = False
    
    def wait(self, timeout=None):
        if self._closed:
            raise IOError(errno.EBADF, os.strerror(errno.EBADF))
        self.hub.poll(self._gun, read=True, timeout=timeout)
        os.read(self._gun, 1)
    
    def pull(self):
        if self._closed:
            raise IOError(errno.EBADF, os.strerror(errno.EBADF))
        while True:
            try:
                os.write(self._trigger, 'x')
            except (IOError, OSError), err:
                if err.args[0] == errno.EINTR:
                    continue
                elif err.args[0] == errno.EAGAIN:
                    return
                raise
            return
    
    def close(self):
        self._closed = True
        for fd in self._gun, self._trigger:
            try:
                os.close(fd)
            except IOError:
                pass
        del self._gun, self._trigger


if __name__ == '__main__':
    import doctest
    doctest.testmod()
