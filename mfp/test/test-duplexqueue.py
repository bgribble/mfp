

from unittest import TestCase 
from mfp.duplex_queue import DuplexQueue, QRequest

import multiprocessing
import threading
import time 

def client_thread(q):
	q.init_responder()
	while True:
		req = q.get()

		# tearDown 
		if req == "quit":
			break
		# test_echo 
		elif isinstance(req, QRequest):
			req.response = req.payload
			q.put(req)
		# test_bare_payload 
		elif req == "ping":
			q.put("pong")

class DuplexQueueTests (TestCase):
	def setUp(self):
		self.reader_info = [ False, None ]
		self.q = DuplexQueue()

		self.client = multiprocessing.Process(target=client_thread, args=(self.q,))
		self.client.start()
		self.q.init_requestor()

	def tearDown(self):
		self.q.put("quit")
		self.q.finish()
		self.client.join()
		pass

	def test_echo(self):
		'''test_echo: echo handler on other end returns same payload'''

		req = self.q.put(QRequest("echo"))
		print "testEcho: waiting"
		self.q.wait(req)
		print "testEcho:", req
		assert req.response == "echo"
		assert req.state == QRequest.RESPONSE_RCVD

	def test_callback(self):
		'''test_callback: local callback triggered on response'''
		r = [False]

		def cb(*args):
			r[0] = True 
		
		req = self.q.put(QRequest("callback", callback=cb))
		self.q.wait(req)
		assert r[0] == True 

	def test_bare_payload(self):
		'''test_bare_payload: ping/pong of bare strings works'''
		pong = [ False ]
		def hand(q, val):
			if val == "pong":
				pong[0] = True
		
		self.q.handler = hand
		self.q.put("ping")
		time.sleep(0.1)
		assert pong[0] == True 
