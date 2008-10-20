"""Utility functions."""


def prefixes(s):
    """Generator yielding all prefixes of s.
    
    >>> list(prefixes('foobar'))
    ['fooba', 'foob', 'foo', 'fo', 'f']
    """
    for i in xrange(len(s) - 1, 0, -1):
        yield s[:i]


if __name__ == '__main__':
    import doctest
    doctest.testmod()
