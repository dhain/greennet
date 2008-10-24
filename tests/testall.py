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

test_modules = (
    'test_hub',
    'test_queue',
)


if __name__ == '__main__':
    suite = unittest.TestSuite()
    doc_suite = unittest.TestSuite()
    for m in modules:
        mod = mod_import(m)
        doc_suite.addTest(doctest.DocTestSuite(mod))
    suite.addTests(doc_suite)
    for m in test_modules:
        mod = mod_import(m)
        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(mod))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
