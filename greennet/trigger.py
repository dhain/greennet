"""A thread-safe way to interrupt a Hub waiting on IO."""


import os

from greennet import get_hub


class Trigger(object):
    def __init__(self, hub=None):
        self.hub = get_hub() if hub is None else hub
        self._gun, self._trigger = os.pipe()
    
    def wait(self, timeout=None):
        self.hub.poll(self._gun, read=True, timeout=timeout)
        os.read(self._gun, 1)
    
    def pull(self):
        while not os.write(self._trigger, 'x'):
            pass


if __name__ == '__main__':
    import doctest
    doctest.testmod()
