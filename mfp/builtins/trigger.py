#! /usr/bin/env python2.6
'''
p_trigger.py: Repeat input on multiple outputs 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp
from .. import Bang, Uninit

class Trigger (Processor):
	'''
	[trigger {n}]

	[trigger] clones its input on multiple outputs, number 
	determined by the creation arg.  Used as a sequencing aid, 
	since outputs will be activated in reverse order of index 
	'''
	def __init__(self, init_type, init_args):

		initargs, kwargs = self.parse_args(init_args)
		if len(initargs) > 0:
			numout = initargs[0]
		else:
			numout = 1
		Processor.__init__(self, 1, numout, init_type, init_args)
		self.outlet_order.reverse() 

	def trigger(self):
		for i in range(len(self.outlets)):
			self.outlets[i] = self.inlets[0]

def register():
	MFPApp().register("trigger", Trigger)

