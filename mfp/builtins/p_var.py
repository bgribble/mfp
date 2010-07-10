#! /usr/bin/env python2.6
'''
p_var.py: Variable holder 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor 
from ..main import MFPApp
from .. import Bang 

class Var (Processor):
	def __init__(self, initval=None):
		self.value = initval
		Processor.__init__(self, inlets=2, outlets=1)

	def trigger(self):
		if self.inlets[1] is not None:
			self.value = self.inlets[1] 
			self.inlets[1] = None 

		if self.inlets[0] is Bang:
			self.outlets[0] = self.value
		else:
			self.value = self.inlets[0]
			self.outlets[0] = self.value	

		self.propagate()

def register():
	MFPApp.register("var", Var)
