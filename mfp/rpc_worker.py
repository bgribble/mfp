#! /usr/bin/env python2.6
'''
rpc_worker.py
multiprocessing-based slave with error handling and communication
'''

from rpc_wrapper import RPCWrapper
from request_pipe import RequestPipe
from request import Request
from shark_pool import SharkPool, PoolShark
import multiprocessing, threading
import Queue
import time

class RPCShark (PoolShark):
	def __init__(self, pool, pipe):
		self.pipe = pipe
		PoolShark.__init__(self, pool)

	def capture(self):
		try:
			bite = self.pipe.get(timeout=0.1)
			return bite
		except Queue.Empty:
			raise SharkPool.Empty()

	def consume(self, bite):
		req = self.pipe.process(bite)
		if req.payload == 'quit':
			# escape takes this thread out of the pool for finish()
			self.escape()
			self.pool.finish()
			# returning False kills this thread 
			return False
		# FIXME was == Request.RESPONSE_PEND in reader_proc
		elif req.state != Request.RESPONSE_RCVD:
			RPCWrapper.handle(req)
			print "RPCWorker.consume putting response", req.state, req.response, req.payload
			self.pipe.put(req)
		else:
			print "RPCWorker.consume ignoring", req, req.state, req.response, req.payload
		return True

def rpc_worker_slave(pipe, initproc, lck):
	RPCWrapper.pipe = pipe
	RPCWrapper.local = True
	
	pipe.init_slave()

	if initproc:
		initproc(pipe)

	# wait until time to quit
	lck.acquire()

class RPCWorker(object):
	def __init__(self, name, initproc=None):
		self.name = name
		self.pipe = RequestPipe(factory=lambda pool: RPCShark(pool, self.pipe))
		self.initproc = initproc
		self.worker_lock = multiprocessing.Lock()
		self.worker_lock.acquire()
		self.worker = multiprocessing.Process(target=rpc_worker_slave,
										      args=(self.pipe, self.initproc, self.worker_lock))
		self.monitor = threading.Thread(target=self.monitor_proc, args=())
		self.quitreq = False

		self.worker.start()
		self.monitor.start()
 
		self.pipe.init_master()

	def serve(self, cls):
		cls.pipe = self.pipe
		cls.local = False

	def monitor_proc(self):
		self.worker.join()
		if not self.quitreq:
			print 'RPCWorker thread EXITED UNEXPECTEDLY'
			self.worker = None

	def finish(self):
		self.quitreq = True
		if self.worker:
			self.pipe.put(Request("quit"))
			self.worker_lock.release()
			self.pipe.finish()
		if self.monitor:
			self.monitor.join()

