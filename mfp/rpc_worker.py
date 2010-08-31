#! /usr/bin/env python2.6
'''
rpc_worker.py
multiprocessing-based slave with error handling and communication
'''

from rpc_wrapper import RPCWrapper
from request_pipe import RequestPipe
from request import Request
import multiprocessing, threading
import Queue

def rpc_worker_slave(pipe, initproc=None):
	def handle_proc(req):
		RPCWrapper.handle(req)
		pipe.put(req)

	pipe.init_slave(reader=False)
	RPCWrapper.pipe = pipe
	RPCWrapper.local = True
	if initproc:
		initproc(pipe)

	threadlist = []
	while True:
		threadsalive = []
		for t in threadlist:
			t.join(timeout=.0001)
			if t.is_alive():
				threadsalive.append(t)
		threadlist = threadsalive

		r = pipe.get()
		
		if r.state == Request.RESPONSE_RCVD:
			continue
		elif r.payload == 'quit':
			break
		else:
			t = threading.Thread(target=handle_proc, args=(r,))
			t.start()
			threadlist.append(t)

class RPCWorker(object):
	def __init__(self, name, initproc=None):
		self.name = name
		self.pipe = RequestPipe()
		self.initproc = initproc
		self.worker = multiprocessing.Process(target=rpc_worker_slave,
										      args=(self.pipe, self.initproc))
		self.monitor = threading.Thread(target=self.monitor_proc, args=())
		self.quitreq = False

		self.worker.start()
		self.monitor.start()
 
		self.pipe.init_master(reader=self.reader_proc)

	def serve(self, cls):
		cls.pipe = self.pipe
		cls.local = False

	def monitor_proc(self):
		self.worker.join()
		if not self.quitreq:
			print 'RPCWorker thread EXITED UNEXPECTEDLY'
			self.worker = None

	def reader_proc(self):
		while not self.quitreq:
			try:
				incoming = self.pipe.get(timeout=0.1)
				
				if incoming.state == Request.RESPONSE_PEND:
					RPCWrapper.handle(incoming)
					self.pipe.put(incoming)
			
			except Queue.Empty:
				pass

	def finish(self):
		self.quitreq = True
		if self.worker:
			self.pipe.put(Request("quit"))
		if self.monitor:
			self.monitor.join()
		self.pipe.finish()

