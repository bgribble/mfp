
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

class StackDepthTest(TestCase):
	def setUp(self):
		self.var = MFPApp.create("var", 0)
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
