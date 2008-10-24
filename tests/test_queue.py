import time
import unittest

import greennet
from greennet.queue import Queue


IMMEDIATE_THRESHOLD = 0.01   # how quick is "immediate"


class TestQueue(unittest.TestCase):
    def setUp(self):
        self.hub = greennet.hub.Hub()
    
    def test_len(self):
        q = Queue(hub=self.hub)
        self.assertEqual(len(q), 0)
        q.append('an item')
        self.assertEqual(len(q), 1)
        q.appendleft('another item')
        self.assertEqual(len(q), 2)
        q.clear()
        self.assertEqual(len(q), 0)
    
    def test_append(self):
        q = Queue(hub=self.hub)
        self.assertEqual(len(q), 0)
        q.append('an item')
        self.assertEqual(len(q), 1)
        self.assertEqual(q.pop(), 'an item')
        q.append('an item')
        q.append('another item')
        self.assertEqual(len(q), 2)
        self.assertEqual(q.pop(), 'another item')
        self.assertEqual(q.pop(), 'an item')
    
    def test_appendleft(self):
        q = Queue(hub=self.hub)
        self.assertEqual(len(q), 0)
        q.appendleft('an item')
        self.assertEqual(len(q), 1)
        self.assertEqual(q.pop(), 'an item')
        q.appendleft('an item')
        q.appendleft('another item')
        self.assertEqual(len(q), 2)
        self.assertEqual(q.pop(), 'an item')
        self.assertEqual(q.pop(), 'another item')
    
    def test_pop(self):
        q = Queue(hub=self.hub)
        self.assertEqual(len(q), 0)
        q.append('an item')
        q.append('another item')
        self.assertEqual(len(q), 2)
        self.assertEqual(q.pop(), 'another item')
        self.assertEqual(len(q), 1)
        self.assertEqual(q.pop(), 'an item')
        self.assertEqual(len(q), 0)
        start = time.time()
        self.assertRaises(greennet.Timeout,
                          q.pop,
                          IMMEDIATE_THRESHOLD)
        self.assert_(time.time() - start < IMMEDIATE_THRESHOLD * 2)
        self.assertEqual(len(q), 0)
    
    def test_popleft(self):
        q = Queue(hub=self.hub)
        self.assertEqual(len(q), 0)
        q.append('an item')
        q.append('another item')
        self.assertEqual(len(q), 2)
        self.assertEqual(q.popleft(), 'an item')
        self.assertEqual(len(q), 1)
        self.assertEqual(q.popleft(), 'another item')
        self.assertEqual(len(q), 0)
        start = time.time()
        self.assertRaises(greennet.Timeout,
                          q.popleft,
                          IMMEDIATE_THRESHOLD)
        self.assert_(time.time() - start < IMMEDIATE_THRESHOLD * 2)
        self.assertEqual(len(q), 0)
    
    def test_full(self):
        q = Queue(1, hub=self.hub)
        self.assertEqual(len(q), 0)
        self.assertFalse(q.full())
        q.append('an item')
        self.assertEqual(len(q), 1)
        self.assert_(q.full())
        q.pop()
        self.assertEqual(len(q), 0)
        self.assertFalse(q.full())
    
    def test_append_full(self):
        q = Queue(1, hub=self.hub)
        q.append('an item')
        self.assertEqual(len(q), 1)
        self.assert_(q.full())
        start = time.time()
        self.assertRaises(greennet.Timeout,
                          q.append,
                          'another_item',
                          IMMEDIATE_THRESHOLD)
        self.assert_(time.time() - start < IMMEDIATE_THRESHOLD * 2)
        self.assertEqual(len(q), 1)
        self.assert_(q.full())
        q.pop()
        q.append('an item')
        self.assertEqual(len(q), 1)
        self.assert_(q.full())
    
    def test_appendleft_full(self):
        q = Queue(1, hub=self.hub)
        q.appendleft('an item')
        self.assertEqual(len(q), 1)
        self.assert_(q.full())
        start = time.time()
        self.assertRaises(greennet.Timeout,
                          q.appendleft,
                          'another_item',
                          IMMEDIATE_THRESHOLD)
        self.assert_(time.time() - start < IMMEDIATE_THRESHOLD * 2)
        self.assertEqual(len(q), 1)
        self.assert_(q.full())
        q.pop()
        q.appendleft('an item')
        self.assertEqual(len(q), 1)
        self.assert_(q.full())


if __name__ == '__main__':
    unittest.main()
