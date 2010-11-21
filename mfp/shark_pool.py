#! /usr/bin/env python2.6
'''
shark_pool.py
Thread pool for processing bites of work
'''

import threading 
import Queue

class PoolShark (object):
	def __init__(self, pool):
		self.pool = pool
		self.quit_req = False
		self.lock = threading.Lock()
		self.condition = threading.Condition(self.lock)
		self.thread = threading.Thread(target=self._thread_func)
		self.thread.start()
	
	def _thread_func(self):
		while not self.quit_req:

			with self.lock:
				# get in line
				self.pool.shark_ready(self)
				if self.pool.active_shark != self:
					self.condition.wait()

			if self.quit_req:
				break

			# capture a chunk of data
			chum = self.capture()

			# consume data
			self.pool.shark_consuming(self)
			self.consume(chum)

		self.pool.shark_done(self)

	def capture(self):
		'''(virtual) Grab next available chunk of data'''
		pass

	def consume(self, data):
		'''(virtual) Process chunk of data'''
		pass

	def go(self):
		with self.lock:
			self.condition.notify()

	def finish(self):
		with self.lock:
			self.quit_req = True
			self.condition.notify()

class SharkPool(object):
	def __init__(self, factory, count=5):
		self.factory = factory
		self.min_sharks = count

		self.lock = threading.Lock()
		self.condition = threading.Condition(self.lock)

		self.reaper = threading.Thread(target=self._reaper_thread)
		self.quit_req = False

		self.active_shark = None
		self.waiting_pool = []
		self.working_pool = []
		self.dead_pool = []


	def start(self):
		for n in range(self.min_sharks):
			self.factory(self)
		
		self.reaper.start()

	def shark_ready(self, shark):
		with self.lock:
			if shark in self.working_pool:
				self.working_pool.remove(shark)
			
			if self.active_shark is None:
				self.active_shark = shark
			else:
				if len(self.waiting_pool) < self.min_sharks:
					self.waiting_pool.append(shark)
				else:
					shark.exit()
					self.dead_pool.append(shark)
			self.condition.notify()

	def shark_consuming(self, shark):
		with self.lock:
			if shark == self.active_shark:
				self.working_pool.append(shark)
				if len(self.waiting_pool):
					self.active_shark = self.waiting_pool.pop()
				else:
					self.active_shark = self.shark_factory()
				self.active_shark.go()
			self.condition.notify()

	def shark_done(self, shark):
		with self.lock:
			if shark in self.waiting_pool:
				self.waiting_pool.remove(shark)
			if shark in self.working_pool:
				self.working_pool.remove(shark)
			if shark in self.dead_pool:
				self.dead_pool.remove(shark)
			self.dead_pool.append(shark)
			self.condition.notify()

	def _reaper_thread(self):
		deadsharks = []
		while not self.quit_req:
			with self.lock:
				self.condition.wait()
				if len(self.dead_pool):
					deadsharks = self.dead_pool
					self.dead_pool = []
			if len(deadsharks):
				for s in deadsharks:
					print "Reaper joining", s
					s.thread.join()
					print "Reaper done", s	
				deadsharks = []

		print "Reaper thread exiting"

	def finish(self):
		with self.lock:
			livesharks = self.waiting_pool + self.working_pool + [self.active_shark]

		for s in livesharks:
			s.finish()

		with self.lock:
			self.quit_req = True
			self.condition.notify()
		print "Joining reaper thread"
		self.reaper.join()
		print "Done"
	
