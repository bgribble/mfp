#! /usr/bin/env python2.6
'''
p_inletoutlet.py: inlet and outlet processors for patches

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor 
from ..main import MFPApp

class Inlet(Processor):
	def __init__(self, init_type, init_args):
		Processor.__init__(self, 1, 1, init_type, init_args)

	def trigger(self):
		self.outlets[0] = self.inlets[0]

class Outlet(Processor):
	def __init__(self, init_type, init_args):
		self.patch = None
		Processor.__init__(self, 1, 1, init_type, init_args)

	def trigger(self):
		if self.patch:
			self.patch.outlets[self.patch.outlet_objects.index(self)] = self.inlets[0]
		self.outlets[0] = self.inlets[0]

def register():
	MFPApp().register("inlet", Inlet)
	MFPApp().register("outlet", Outlet)

