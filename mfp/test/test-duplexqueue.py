

from unittest import TestCase 
from mfp.request_pipe import RequestPipe, Request

import multiprocessing
import threading
import time 

def client_thread(q):
	q.init_slave(reader=False)
	while True:
		req = q.get()
		print "client thread: got request", req
		# tearDown 
		if req == "quit":
			break
		# test_echo 
		elif isinstance(req, Request):
			req.response = req.payload
			q.put(req)
		# test_bare_payload 
		elif req == "ping":
			q.put("pong")

class RequestPipeTests (TestCase):
	def setUp(self):
		self.reader_info = [ False, None ]
		self.pipe = RequestPipe()

		self.client = multiprocessing.Process(target=client_thread, args=(self.pipe,))
		self.client.start()
		self.pipe.init_master()
		time.sleep(0.25)

	def tearDown(self):
		self.pipe.put("quit")
		self.pipe.finish()
		self.client.join()
		pass

	def test_echo(self):
		'''test_echo: echo handler on other end returns same payload'''

		req = self.pipe.put(Request("echo"))
		print "testEcho: waiting"
		self.pipe.wait(req)
		print "testEcho:", req
		assert req.response == "echo"
		assert req.state == Request.RESPONSE_RCVD

	def test_callback(self):
		'''test_callback: local callback triggered on response'''
		r = [False]

		def cb(*args):
			print "callback called", args
			r[0] = True 
		
		req = self.pipe.put(Request("callback", callback=cb))
		self.pipe.wait(req)
		assert r[0] == True 

	def test_bare_payload(self):
		'''test_bare_payload: ping/pong of bare strings works'''
		pong = [ False ]
		def hand(q, val):
			print "test: handler called", val
			if val == "pong":
				pong[0] = True
		
		self.pipe.handler = hand
		print "test: calling put"
		self.pipe.put("ping")
		print "test: back from put"
		time.sleep(0.5)
		assert pong[0] == True 



