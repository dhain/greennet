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
    
    def test_pop_wait_for_append(self):
        q = Queue(hub=self.hub)
        timeout = 0.5
        self.hub.call_later(greennet.greenlet(q.append), timeout, 'an item')
        start = time.time()
        self.assertEqual(q.pop(), 'an item')
        duration = time.time() - start
        self.assert_(duration < timeout + IMMEDIATE_THRESHOLD
                     and duration > timeout - IMMEDIATE_THRESHOLD)
    
    def test_popleft_wait_for_append(self):
        q = Queue(hub=self.hub)
        timeout = 0.5
        self.hub.call_later(greennet.greenlet(q.append), timeout, 'an item')
        start = time.time()
        self.assertEqual(q.popleft(), 'an item')
        duration = time.time() - start
        self.assert_(duration < timeout + IMMEDIATE_THRESHOLD
                     and duration > timeout - IMMEDIATE_THRESHOLD)
    
    def test_pop_wait_for_appendleft(self):
        q = Queue(hub=self.hub)
        timeout = 0.5
        self.hub.call_later(greennet.greenlet(q.appendleft),
                            timeout, 'an item')
        start = time.time()
        self.assertEqual(q.pop(), 'an item')
        duration = time.time() - start
        self.assert_(duration < timeout + IMMEDIATE_THRESHOLD
                     and duration > timeout - IMMEDIATE_THRESHOLD)
    
    def test_popleft_wait_for_appendleft(self):
        q = Queue(hub=self.hub)
        timeout = 0.5
        self.hub.call_later(greennet.greenlet(q.appendleft),
                            timeout, 'an item')
        start = time.time()
        self.assertEqual(q.popleft(), 'an item')
        duration = time.time() - start
        self.assert_(duration < timeout + IMMEDIATE_THRESHOLD
                     and duration > timeout - IMMEDIATE_THRESHOLD)
    
    def test_append_wait_for_pop(self):
        q = Queue(1, hub=self.hub)
        q.append('an item')
        timeout = 0.5
        self.hub.call_later(greennet.greenlet(q.pop), timeout)
        start = time.time()
        q.append('an item')
        duration = time.time() - start
        self.assert_(duration < timeout + IMMEDIATE_THRESHOLD
                     and duration > timeout - IMMEDIATE_THRESHOLD)
        self.assertEqual(q.pop(), 'an item')
    
    def test_appendleft_wait_for_pop(self):
        q = Queue(1, hub=self.hub)
        q.append('an item')
        timeout = 0.5
        self.hub.call_later(greennet.greenlet(q.pop), timeout)
        start = time.time()
        q.appendleft('an item')
        duration = time.time() - start
        self.assert_(duration < timeout + IMMEDIATE_THRESHOLD
                     and duration > timeout - IMMEDIATE_THRESHOLD)
        self.assertEqual(q.pop(), 'an item')
    
    def test_append_wait_for_popleft(self):
        q = Queue(1, hub=self.hub)
        q.append('an item')
        timeout = 0.5
        self.hub.call_later(greennet.greenlet(q.popleft), timeout)
        start = time.time()
        q.append('an item')
        duration = time.time() - start
        self.assert_(duration < timeout + IMMEDIATE_THRESHOLD
                     and duration > timeout - IMMEDIATE_THRESHOLD)
        self.assertEqual(q.pop(), 'an item')
    
    def test_appendleft_wait_for_popleft(self):
        q = Queue(1, hub=self.hub)
        q.append('an item')
        timeout = 0.5
        self.hub.call_later(greennet.greenlet(q.popleft), timeout)
        start = time.time()
        q.appendleft('an item')
        duration = time.time() - start
        self.assert_(duration < timeout + IMMEDIATE_THRESHOLD
                     and duration > timeout - IMMEDIATE_THRESHOLD)
        self.assertEqual(q.pop(), 'an item')
    
    def test_clear(self):
        q = Queue(hub=self.hub)
        q.append('an item')
        q.append('another item')
        self.assertEqual(len(q), 2)
        q.clear()
        self.assertEqual(len(q), 0)
    
    def test_append_wait_for_clear(self):
        q = Queue(1, hub=self.hub)
        q.append('an item')
        timeout = 0.5
        self.hub.call_later(greennet.greenlet(q.clear), timeout)
        start = time.time()
        q.append('an item')
        duration = time.time() - start
        self.assert_(duration < timeout + IMMEDIATE_THRESHOLD
                     and duration > timeout - IMMEDIATE_THRESHOLD)
        self.assertEqual(q.pop(), 'an item')
    
    def test_appendleft_wait_for_clear(self):
        q = Queue(1, hub=self.hub)
        q.append('an item')
        timeout = 0.5
        self.hub.call_later(greennet.greenlet(q.clear), timeout)
        start = time.time()
        q.appendleft('an item')
        duration = time.time() - start
        self.assert_(duration < timeout + IMMEDIATE_THRESHOLD
                     and duration > timeout - IMMEDIATE_THRESHOLD)
        self.assertEqual(q.pop(), 'an item')
    
    def test_wait_until_empty_on_pop(self):
        q = Queue(hub=self.hub)
        q.append('an item')
        q.append('another item')
        timeout = 0.5
        self.hub.call_later(greennet.greenlet(q.pop), timeout)
        self.hub.call_later(greennet.greenlet(q.pop), timeout * 2)
        start = time.time()
        q.wait_until_empty()
        duration = time.time() - start
        self.assert_(duration < timeout * 2 + IMMEDIATE_THRESHOLD
                     and duration > timeout * 2 - IMMEDIATE_THRESHOLD)
    
    def test_wait_until_empty_on_popleft(self):
        q = Queue(hub=self.hub)
        q.append('an item')
        q.append('another item')
        timeout = 0.5
        self.hub.call_later(greennet.greenlet(q.popleft), timeout)
        self.hub.call_later(greennet.greenlet(q.popleft), timeout * 2)
        start = time.time()
        q.wait_until_empty()
        duration = time.time() - start
        self.assert_(duration < timeout * 2 + IMMEDIATE_THRESHOLD
                     and duration > timeout * 2 - IMMEDIATE_THRESHOLD)
    
    def test_wait_until_empty_on_clear(self):
        q = Queue(hub=self.hub)
        q.append('an item')
        q.append('another item')
        timeout = 0.5
        self.hub.call_later(greennet.greenlet(q.clear), timeout)
        start = time.time()
        q.wait_until_empty()
        duration = time.time() - start
        self.assert_(duration < timeout + IMMEDIATE_THRESHOLD
                     and duration > timeout - IMMEDIATE_THRESHOLD)
    
    def test_wait_until_empty_timeout(self):
        q = Queue(hub=self.hub)
        q.append('an item')
        start = time.time()
        self.assertRaises(greennet.Timeout,
                          q.wait_until_empty,
                          IMMEDIATE_THRESHOLD)
        self.assert_(time.time() - start < IMMEDIATE_THRESHOLD * 2)


if __name__ == '__main__':
    unittest.main()
