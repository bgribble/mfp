

from unittest import TestCase 
from mfp.duplex_queue import DuplexQueue, QRequest

import multiprocessing
import threading


def client_thread(q):
	q.init_responder()
	while True:
		req = q.get()
		if req == "quit":
			break
		elif isinstance(req, QRequest):
			req.response = req.payload
			q.put(req)

def reader_thread(q, quit_req):
	while not quit_req[0]:
		resp = q.get(timeout=0.1)

class DuplexQueueTests (TestCase):
	def setUp(self):
		self.q = DuplexQueue()

		self.client = multiprocessing.Process(target=client_thread, args=(self.q,))
		self.client.start()
		self.q.init_requestor()

		self.reader_req = [ False ]
		self.reader = threading.Thread(target=reader_thread, args=(self.q, self.reader_req))
		self.reader.start()

	def tearDown(self):
		self.q.put("quit")
		self.reader_req[0] = True 
		self.reader.join()
		self.client.join()
		pass

	def testEcho(self):
		'''testEcho: echo handler on other end returns same payload'''

		req = self.q.put(QRequest("echo"))
		print "testEcho: waiting"
		self.q.wait(req)
		print "testEcho:", req
		assert req.response == "echo"
		assert req.state == QRequest.RESPONSE_RCVD

	def testCallback(self):
		'''testCallback: local callback triggered on response'''
		r = [False]

		def cb(*args):
			r[0] = True 
		
		req = self.q.put(QRequest("callback", callback=cb))
		self.q.wait(req)
		assert r[0] == True 
