#! /usr/bin/env python2.6
'''
request_pipe.pt
Duplex multiprocessing pipe implementation with request/response model
'''
import multiprocessing 
import threading 
import Queue

from request import Request

class RequestPipe(object): 
	def __init__(self):
		master, slave = multiprocessing.Pipe()

		self.role = None

		# the slave will switch these 
		self.this_end = master 
		self.that_end = slave
		self.handler = None
		self.quit_flag = False 

		# management objects for those waiting for a response 
		self.lock = None
		self.condition = None 
		self.pending = {} 
		self.reader_thread = None

		self.finish_callbacks = []

	def _reader_func(self):
		while not self.quit_flag:
			try:
				incoming = self.get(timeout=0.1)
				if self.handler:
					self.handler(self, incoming)
			except Queue.Empty:
				pass

	def on_finish(self, cbk):
		self.finish_callbacks.append(cbk)

	def finish(self):
		self.quit_flag = True
		if self.reader_thread:
			self.reader_thread.join()
		for cbk in self.finish_callbacks:
			cbk()

	def init_master(self, reader=None):
		self.lock = threading.Lock()
		self.condition = threading.Condition(self.lock)
		self.role = 1

		if reader is None:
			reader = self._reader_func
		if reader:
			self.reader_thread = threading.Thread(target=reader)
			self.reader_thread.start()

	def init_slave(self, reader=None):
		'''Reverse ends of pipe; to be used by the slave process'''
		q = self.this_end
		self.this_end = self.that_end
		self.that_end = q
		self.lock = threading.Lock()
		self.condition = threading.Condition(self.lock)
		self.role = 0

		if reader is None:
			reader = self._reader_func
		if reader:
			self.reader_thread = threading.Thread(target=reader)
			self.reader_thread.start()


	def put(self, req):
		tosend = {} 
		if isinstance(req, Request):
			if req.state == Request.CREATED:
				self.pending[req.request_id] = req
				origin = self.role
				req.state = Request.SUBMITTED
			else: 
				origin = not self.role
				req.state = Request.SUBMITTED

			req.queue = self
			tosend['type'] = 'Request'
			tosend['request_id'] = req.request_id
			tosend['payload'] = req.payload 
			tosend['response'] = req.response 
			tosend['origin'] = origin
		else:
			tosend['type'] = 'payload'
			tosend['payload'] = req
		self.this_end.send(tosend)

		return req
	
	def wait(self, req):
		if not isinstance(req, Request):
			return False 

		with self.lock:
			while req.state != Request.RESPONSE_RCVD:
				self.condition.wait()

	def get(self, timeout=None):
		if timeout is not None:
			ready = self.this_end.poll(timeout)
			if not ready:
				raise Queue.Empty
		try:
			qobj = self.this_end.recv()
		except EOFError, e:
			raise Queue.Empty 

		req = None 
		if qobj.get('type') == 'Request':
			if self.pending is not None and qobj.get('origin') == self.role: 
				req = self.pending.get(qobj.get('request_id'))
			else:
				req = None
				
			if req:
				req.response = qobj.get('response')
				req.payload = qobj.get('payload')
				req.state = Request.RESPONSE_RCVD
				del self.pending[req.request_id]
				if req.callback is not None:
					req.callback(req)
			else:
				req = Request(qobj.get('payload'))
				req.request_id = qobj.get('request_id')
				req.state = Request.RESPONSE_PEND
			qobj = req
		else:
			qobj = qobj.get('payload')

		with self.lock:
			self.condition.notify()
		return qobj

	
