
from unittest import TestCase
from mfp.main import MFPApp
from mfp import Bang 
from mfp.processor import Processor 

class LimitedIncr (Processor):
	def __init__(self, limit=0):
		self.limit = limit
		self.lastval = None
		Processor.__init__(self, inlets=1, outlets=1)

	def trigger(self):
		if self.inlets[0] < self.limit:
			self.outlets[0] = self.inlets[0] + 1
			self.lastval = self.outlets[0]

class FanOut (Processor):
	trail = [] 
	def __init__(self, tag):
		self.tag = tag 
		Processor.__init__(self, inlets=1, outlets=4)

	def trigger(self):
		self.outlets[0] = self.outlets[1] = self.outlets[2] = self.outlets[3] = Bang
		FanOut.trail.append(self.tag)

class StackDepthTest(TestCase):
	def setUp(self):
		self.var = MFPApp.create("var", "0")
		self.inc = LimitedIncr()
		self.var.connect(0, self.inc, 0)
		self.inc.connect(0, self.var, 0)

	def test_100(self):
		'''test_100: 100 recursions doesn't overflow stack'''
		self.inc.limit = 100
		self.var.send(0, 0)
		print "Last value:", self.inc.lastval
		self.assertEqual(self.var.status, Processor.OK)
		self.assertEqual(self.inc.lastval, 100)


	def test_1000(self):
		'''test_1000: 1000 recursions doesn't overflow stack'''
		self.inc.limit = 1000
		self.var.send(0, 0)
		print "Last value:", self.inc.lastval
		self.assertEqual(self.var.status, Processor.OK)
		self.assertEqual(self.inc.lastval, 1000)
	
	def test_10000(self):
		'''test_10000: 10000 recursions doesn't overflow stack'''
		self.inc.limit = 10000
		self.var.send(0, 0)
		print "Last value:", self.inc.lastval
		self.assertEqual(self.var.status, Processor.OK)
		self.assertEqual(self.inc.lastval, 10000)
	
	def test_100000(self):
		'''test_100000: 100000 recursions doesn't overflow stack'''
		self.inc.limit = 100000
		self.var.send(0, 0)
		print "Last value:", self.inc.lastval
		self.assertEqual(self.var.status, Processor.OK)
		self.assertEqual(self.inc.lastval, 100000)

class DepthFirstTest(TestCase):
	def setUp(self):
		FanOut.trail = [] 
		self.procs = [ FanOut(i) for i in range(0, 10) ]
		for i in range(1, 5):
			self.procs[0].connect(i-1, self.procs[i], 0)
		for i in range(5, 9):
			self.procs[1].connect(i-5, self.procs[i], 0)
		self.procs[3].connect(0, self.procs[9], 0)

	def test_depthfirst(self):
		'''test_depthfirst: depth-first execution order is preserved''' 
		self.procs[0].send(Bang, 0)
		print FanOut.trail
		self.assertEqual(FanOut.trail, [0, 1, 5, 6, 7, 8, 2, 3, 9, 4])

