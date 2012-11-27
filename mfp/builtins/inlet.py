#! /usr/bin/env python2.6
'''
p_inlet.py: Patch inlet/outlet builtins

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from mfp.main import MFPApp

class Inlet(Processor):
	def __init__(self, init_type, init_args):
		Processor.__init__(self, 1, 1, init_type, init_args)

	def trigger(self):
		self.outlets[0] = self.inlets[0]

class Outlet(Processor):
	pass
