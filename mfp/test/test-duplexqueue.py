

from unittest import TestCase 
from mfp.request_pipe import RequestPipe, RequestShark, Request
from mfp.shark_pool import SharkPool
import multiprocessing
import Queue
import threading
import time 


def client_thread(pipe, lck):
	pipe.init_slave()

	lck.acquire()

class TestShark(RequestShark):
	def consume(self, bite):
		print "client shark: got request", bite 
		req = self.pipe.process(bite)

		# tearDown 
		if req == "quit":
			return False
		# test_echo 
		elif isinstance(req, Request) and req.state == Request.RESPONSE_PEND:
			req.response = req.payload
			self.pipe.put(req)
		# test_bare_payload 
		elif req == "ping":
			self.pipe.put("pong")
		return True

class RequestPipeTests (TestCase):
	def setUp(self):
		self.reader_info = [ False, None ]
		self.pipe = RequestPipe(factory=lambda pool: TestShark(pool, self.pipe))
		self.lck = multiprocessing.Lock()
		self.lck.acquire()
		self.client = multiprocessing.Process(target=client_thread, args=(self.pipe, self.lck))
		self.client.start()
		self.pipe.init_master()
		time.sleep(0.25)

	def tearDown(self):
		self.pipe.put("quit")
		self.lck.release()
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
		print
	
		def cb(*args):
			print "callback called", args
			r[0] = True 
		
		req = self.pipe.put(Request("callback", callback=cb))
		print "put request", req
		self.pipe.wait(req)
		print "wait returned"
		assert r[0] == True 



