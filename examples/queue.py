from py.magic import greenlet

import greennet
from greennet.queue import Queue


def popper(queue):
    print queue.pop()


if __name__ == '__main__':
    queue = Queue()
    greennet.schedule(greenlet(popper), queue)
    queue.append('hello world')
    greennet.run()

