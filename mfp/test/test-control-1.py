
from unittest import TestCase 
from mfp.main import MFPApp

import mfp 
from mfp import Bang 

def setup():
	mfp.builtins.register()

class PlusTest(TestCase):
	def setUp(self):
		self.plus = MFPApp.create("+")
		self.out = MFPApp.create("var")
		self.plus.connect(0, self.out, 0)

	def test_default(self):
		'''test with default creation args'''
		self.plus = MFPApp.create("+", 12)
		self.plus.connect(0, self.out, 0)
		self.plus.send(13, 0)
		assert self.out.outlets[0] == 25

		self.plus.send(99, 0)
		assert self.out.outlets[0] == 111

	def test_numbers(self):
		'''test_numbers: 23 + 32 == 55'''
		self.plus.send(23, 1)
		self.plus.send(32, 0)
		assert self.out.outlets[0] == 55

	def test_strings(self):
		'''test_strings: 'hello ' + 'world' == 'hello world' '''
		self.plus.send("world", 1)
		self.plus.send("hello ", 0)
		assert self.out.outlets[0] == "hello world"

	def test_typeerr(self):
		'''test_typeerr: mismatched types produce nothing'''
		self.plus.send("hello", 1)
		self.plus.send(5, 0)

		assert self.out.outlets[0] is None

class PrintTest(TestCase):
	def setUp(self):
		self.pr = MFPApp.create("print")
		self.out = MFPApp.create("var")
		self.pr.connect(0, self.out, 0)

	def test_default(self):
		'''[print] uses default formatter'''

		self.pr.send("hello, world")
		assert self.out.outlets[0] == "hello, world"

		self.pr.send(123)
		assert self.out.outlets[0] == "123"

	def test_string_format(self):
		'''[print] will use format given on inlet 1'''
		
		self.pr.send("%.3s", 1)
		self.pr.send(False)
		assert self.out.outlets[0] == "Fal"

	def test_seq_format(self):
		'''[print] will apply tuple to multiple args, but not list'''

		self.pr.send("%s %s %s", 1)
		self.pr.send([1, 2, 3])

		assert self.out.outlets[0] == None
		
		self.pr.send((1, 2, 3))

		assert self.out.outlets[0] == "1 2 3"

class RouteTest (TestCase):
	def setUp(self):
		self.r = MFPApp.create("route", False, 1, "hello")

	def test_basic_routing(self):
		'''[route] works in simple cases'''
		self.r.send([False, True], 0)
		assert self.r.outlets[0] == [ True ] 
		assert self.r.outlets[1] == None  
		assert self.r.outlets[2] == None
		assert self.r.outlets[3] == None 

		self.r.send([1, 2, 3], 0)
		assert self.r.outlets[0] == None  
		assert self.r.outlets[1] == [2, 3] 
		assert self.r.outlets[2] == None
		assert self.r.outlets[3] == None 

		self.r.send((1, 2, 3), 0)
		assert self.r.outlets[0] == None  
		assert self.r.outlets[1] == (2, 3) 
		assert self.r.outlets[2] == None
		assert self.r.outlets[3] == None 

		self.r.send('hello', 0)
		assert self.r.outlets[0] == None  
		assert self.r.outlets[1] == None 
		assert self.r.outlets[2] == Bang
		assert self.r.outlets[3] == None 

		self.r.send('unmatched', 0)
		assert self.r.outlets[0] == None  
		assert self.r.outlets[1] == None 
		assert self.r.outlets[2] == None
		assert self.r.outlets[3] == 'unmatched' 

		self.r.send(['unmatched', 2], 0)
		assert self.r.outlets[0] == None  
		assert self.r.outlets[1] == None 
		assert self.r.outlets[2] == None
		assert self.r.outlets[3] == ['unmatched', 2] 

	def test_reset_addresses(self):
		'''[route] can change its addresses on the fly '''
		self.r.send([1,2], 1)
		self.r.send([1, True], 0)
		assert len(self.r.outlets) == 3

		assert self.r.outlets[0] == [True] 
		assert self.r.outlets[1] == None 
		assert self.r.outlets[2] == None

		self.r.send([2, False], 0)
		assert self.r.outlets[0] == None
		assert self.r.outlets[1] == [False]  
		assert self.r.outlets[2] == None

		self.r.send('unmatched', 0)
		assert self.r.outlets[0] == None
		assert self.r.outlets[1] == None 
		assert self.r.outlets[2] == 'unmatched'

	def test_connections_ok(self):
		'''[route] --> [var] connection remains when addresses resized'''
		v = MFPApp.create("var")
		self.r.connect(0, v, 0)
		self.r.send([4], 1)
		self.r.send([4, 'hello'], 0)
		assert v.outlets[0] == ['hello']



