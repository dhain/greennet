

def prefixes(s):
    """Generator yielding all prefixes of s.
    
    Ie. if s == 'foobar', prefixes will yield:
        'fooba',
        'foob',
        'foo',
        'fo', and
        'f'.
    """
    for i in xrange(len(s) - 1, 0, -1):
        yield s[:i]

