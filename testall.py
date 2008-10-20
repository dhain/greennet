import unittest
import doctest


def mod_import(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


modules = (
    'greennet',
    'greennet.hub',
    'greennet.queue',
    'greennet.ssl',
    'greennet.util',
)


if __name__ == '__main__':
    suite = unittest.TestSuite()
    for m in modules:
        mod = mod_import(m)
        suite.addTest(doctest.DocTestSuite(mod))
    runner = unittest.TextTestRunner()
    runner.run(suite)
