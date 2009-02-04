import time
import socket
import unittest

import greennet


IMMEDIATE_THRESHOLD = 0.01   # how quick is "immediate"


class TestHub(unittest.TestCase):
    def setUp(self):
        self.hub = greennet.hub.Hub()
    
    def test_sleep(self):
        timeout = 0.5
        start = time.time()
        self.hub.sleep(timeout)
        duration = time.time() - start
        self.assert_(duration < timeout + IMMEDIATE_THRESHOLD
                     and duration > timeout - IMMEDIATE_THRESHOLD)
    
    def test_call_later(self):
        a = [0]
        def task():
            a[0] = 1
        timeout = 0.5
        start = time.time()
        self.hub.call_later(greennet.greenlet(task), timeout)
        self.hub.run()
        duration = time.time() - start
        self.assert_(duration < timeout + IMMEDIATE_THRESHOLD
                     and duration > timeout - IMMEDIATE_THRESHOLD)
        self.assertEqual(a[0], 1)
    
    def test_call_later_with_args(self):
        a = [0]
        def task(arg1, arg2, *args):
            a.append(arg1)
            a.append(arg2)
            a.extend(args)
        timeout = 0.5
        start = time.time()
        self.hub.call_later(greennet.greenlet(task), timeout, 1, 2, *(3, 4))
        self.hub.run()
        duration = time.time() - start
        self.assert_(duration < timeout + IMMEDIATE_THRESHOLD
                     and duration > timeout - IMMEDIATE_THRESHOLD)
        self.assertEqual(a, [0, 1, 2, 3, 4])
    
    def test_run(self):
        a = [0, 0]
        def task1():
            a[0] = 1
        def task2():
            a[1] = 1
        self.hub.schedule(greennet.greenlet(task1))
        self.hub.schedule(greennet.greenlet(task2))
        self.hub.run()
        self.assertEqual(a[0], 1)
        self.assertEqual(a[1], 1)
    
    def test_schedule(self):
        a = [0]
        def task():
            a[0] = 1
        self.hub.schedule(greennet.greenlet(task))
        self.hub.run()
        self.assertEqual(a[0], 1)
    
    def test_schedule_with_args(self):
        a = [0]
        def task(arg1, arg2, *args):
            a.append(arg1)
            a.append(arg2)
            a.extend(args)
        self.hub.schedule(greennet.greenlet(task),
                          1, 2, *(3, 4))
        self.hub.run()
        self.assertEqual(a, [0, 1, 2, 3, 4])
    
    def test_switch(self):
        a = [0]
        def task():
            a[0] = 1
            self.hub.switch()
            self.assertEqual(a[0], 2)
            a[0] = 3
        self.hub.schedule(greennet.greenlet(task))
        self.hub.switch()
        self.assertEqual(a[0], 1)
        a[0] = 2
        self.hub.run()
        self.assertEqual(a[0], 3)


class TestHubWithSockets(unittest.TestCase):
    def setUp(self):
        self.hub = greennet.hub.Hub()
        self.s1, self.s2 = socket.socketpair()
        self.s1.setblocking(False)
        self.s2.setblocking(False)
    
    def tearDown(self):
        self.s1.close()
        self.s2.close()
    
    def test_poll_writeable(self):
        start = time.time()
        self.hub.poll(self.s1, write=True, timeout=IMMEDIATE_THRESHOLD + 1)
        self.assert_(time.time() - start < IMMEDIATE_THRESHOLD)
        self.s1.send('some data')
    
    def test_poll_writeable_timeout(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        start = time.time()
        self.assertRaises(greennet.Timeout,
                          self.hub.poll,
                          sock,
                          write=True,
                          timeout=IMMEDIATE_THRESHOLD)
        self.assert_(time.time() - start < IMMEDIATE_THRESHOLD * 2)
    
    def test_poll_readable(self):
        self.s2.send('some data')
        start = time.time()
        self.hub.poll(self.s1, read=True, timeout=IMMEDIATE_THRESHOLD + 1)
        self.assert_(time.time() - start < IMMEDIATE_THRESHOLD)
    
    def test_poll_readable_timeout(self):
        start = time.time()
        self.assertRaises(greennet.Timeout,
                          self.hub.poll,
                          self.s1,
                          read=True,
                          timeout=IMMEDIATE_THRESHOLD)
        self.assert_(time.time() - start < IMMEDIATE_THRESHOLD * 2)
    
    def test_poll_exc(self):
        pass
    
    def test_poll_exc_timeout(self):
        pass


if __name__ == '__main__':
    unittest.main()
