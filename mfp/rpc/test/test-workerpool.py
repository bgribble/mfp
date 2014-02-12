

from unittest import TestCase
from ..worker_pool import WorkerPool, BaseWorker
import Queue

import time


class QueueWorker(BaseWorker):

    workers = []

    def __init__(self, pool, q, results):
        self.queue = q
        self.results = results
        BaseWorker.__init__(self, pool)
        QueueWorker.workers.append(self)

    def take_work(self):
        try:
            bite = self.queue.get(timeout=0.1)
            return bite
        except Queue.Empty:
            raise WorkerPool.Empty()

    def perform_work(self, data):
        self.results.append(data)


class WorkerPoolTest(TestCase):

    def setUp(self):
        self.queue = Queue.Queue()
        self.results = []
        self.pool = WorkerPool(lambda p: QueueWorker(p, self.queue, self.results))
        self.pool.start()

    def tearDown(self):
        self.pool.finish()

        QueueWorker.workers = []

    def test_start(self):
        time.sleep(0.2)
        self.assertEqual(len(QueueWorker.workers), 5)
        self.assertEqual(len(self.pool.waiting_pool), 4)

    def test_1(self):
        self.queue.put(1)
        time.sleep(0.2)
        self.assertEqual(self.results, [1])

    def test_20(self):
        for n in xrange(20):
            self.queue.put(n)
        time.sleep(0.2)
        self.results.sort()
        self.assertEqual(self.results, range(20))
