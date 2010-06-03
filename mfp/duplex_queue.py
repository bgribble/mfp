#! /usr/bin/env python2.6
'''
duplex_queue.py
Duplex multiprocessing queue implementation with request/response model
'''
import multiprocessing 
import threading 
import Queue

class QRequest(object):
	_next_id = 0 

	CREATED = 0 
	SUBMITTED = 1
	RESPONSE_PEND = 2
	RESPONSE_RCVD = 3 
	
	def __init__(self, payload, callback=None, multi_cb=False):
		self.state = QRequest.CREATED 
		self.payload = payload
		self.response = None 
		self.callback = callback
		self.multi_cb = multi_cb
		self.request_id = QRequest._next_id
		QRequest._next_id += 1
	


class DuplexQueue(object): 
	def __init__(self):
		self.read_queue = multiprocessing.Queue()
		self.write_queue = multiprocessing.Queue()
		self.handler = None
		self.quit_flag = False 

		# management objects for those waiting for a response 
		self.lock = None
		self.condition = None 
		self.pending = {} 
		self.reader_thread = None

	def _reader_func(self):
		while not self.quit_flag:
			try:
				incoming = self.get(timeout=0.1)
				if self.handler:
					self.handler(self, incoming)
			except Queue.Empty:
				pass

	def finish(self):
		self.quit_flag = True
		self.reader_thread.join()

	def init_requestor(self):
		self.lock = threading.Lock()
		self.condition = threading.Condition(self.lock)
		self.reader_thread = threading.Thread(target=self._reader_func)
		self.reader_thread.start()

	def init_responder(self):
		'''Reverse read/write queues; to be used by the slave process'''
		q = self.write_queue
		self.write_queue = self.read_queue
		self.read_queue = q
		self.lock = threading.Lock()
		self.condition = threading.Condition(self.lock)

	def put(self, req):
		tosend = {} 
		if isinstance(req, QRequest):
			req.state = QRequest.SUBMITTED
			req.queue = self
			self.pending[req.request_id] = req
			tosend['type'] = 'QRequest'
			tosend['request_id'] = req.request_id
			tosend['payload'] = req.payload 
			tosend['response'] = req.response 
		else:
			tosend['type'] = 'payload'
			tosend['payload'] = req
		print "DuplexQueue.put:", tosend 
		self.write_queue.put(tosend)
		return req
	
	def wait(self, req):
		if not isinstance(req, QRequest):
			return False 

		with self.lock:
			while req.state != QRequest.RESPONSE_RCVD:
				self.condition.wait()

	def get(self, timeout=None):
		try:
			qobj = self.read_queue.get(timeout=timeout)
		except Queue.Empty, e:
			raise

		if qobj.get('type') == 'QRequest':
			req = self.pending.get(qobj.get('request_id'))
			print "DuplexQueue.get: looked up", qobj.get('request_id'), "found", req
			print self.pending 
			if req:
				req.response = qobj.get('response')
				req.state = QRequest.RESPONSE_RCVD
				del self.pending[req.request_id]
				if req.callback is not None:
					req.callback(req)
			else:
				req = QRequest(qobj.get('payload'))
				req.request_id = qobj.get('request_id')
				req.state = QRequest.RESPONSE_PEND
			qobj = req
		else:
			qobj = qobj.get('payload')

		with self.lock:
			self.condition.notify()
		return qobj

	
