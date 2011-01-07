

from unittest import TestCase
from ..shark_pool import SharkPool, PoolShark
import Queue

import time

class QueueShark(PoolShark):

	sharks = []

	def __init__(self, pool, q, results):
		print self
		self.queue = q
		self.results = results
		PoolShark.__init__(self, pool)
		QueueShark.sharks.append(self)
		
	def capture(self):
		try:
			bite = self.queue.get(timeout=0.1)
			return bite
		except Queue.Empty:
			raise SharkPool.Empty()

	def consume(self, data):
		self.results.append(data)

class SharkPoolTest(TestCase):

	def setUp(self):
		self.queue = Queue.Queue()
		self.results = []
		self.pool = SharkPool(lambda p: QueueShark(p, self.queue, self.results))
		self.pool.start()

	def tearDown(self):
		self.pool.finish()
		
		QueueShark.sharks = []

	def test_start(self):
		time.sleep(0.2)
		self.assertEqual(len(QueueShark.sharks), 5)
		self.assertEqual(len(self.pool.waiting_pool), 4)
		

	def test_1(self):
		self.queue.put(1)
		time.sleep(0.2)
		self.assertEqual(self.results, [1])

	def test_20(self):
		for n in xrange(20):
			self.queue.put(n)
		time.sleep(0.2)
		print self.results
		self.results.sort()
		self.assertEqual(self.results, range(20))
