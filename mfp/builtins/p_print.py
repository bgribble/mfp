#! /usr/bin/env python2.6
'''
p_print.py: Debugging print processor 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp
from ..bang import Uninit 

class Print (Processor): 
	def __init__(self, init_type, init_args):
		Processor.__init__(self, 2, 1, init_type, init_args)
		initargs, kwargs = self.parse_args(init_args)
		if len(initargs):
			self.format_string = initargs[0] 
		else:
			self.format_string = "%s"

	def trigger(self):
		if self.inlets[1] is not Uninit:
			self.format_string = self.inlets[1]

		if self.inlets[0] is not Uninit:
			try:
				out = self.format_string % self.inlets[0]
			except TypeError, e:
				if not self.format_string:
					leader = ''
				else:
					leader = self.format_string + ' '

				out = leader + str(self.inlets[0])

			self.outlets[0] = out 
			print out 
			
def register():
	MFPApp().register("print", Print)
