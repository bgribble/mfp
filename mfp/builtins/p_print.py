#! /usr/bin/env python2.6
'''
p_print.py: Debugging print processor 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp
from ..bang import Uninit 

class Print (Processor): 
	def __init__(self, fmt_string="%s"):
		self.format_string = fmt_string 
		Processor.__init__(self, inlets=2, outlets=1)

	def trigger(self):
		if self.inlets[1] is not Uninit:
			self.format_string = self.inlets[1]

		if self.inlets[0] is not Uninit:
			out = self.format_string % self.inlets[0]
			self.outlets[0] = out 
			print out 
			
def register():
	MFPApp.register("print", Print)
