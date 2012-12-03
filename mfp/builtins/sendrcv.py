#! /usr/bin/env python
'''
sendrcv.py: Bus/virtual wire objects.  

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor 
from ..main import MFPApp

class Send (Processor):
	def __init__ (init_type, init_args, patch, scope, name):
		self.dest_name = None 
		self.dest_inlet = 0
		self.dest_obj = None 
		
		initargs, kwargs = self.parse_args(init_args)
		if len(initargs) > 1:
			self.dest_inlet = initargs[1]
		if len(initargs):
			self.dest_name = initargs[0] 
		
		Processor.__init__(self, 1, 0, init_type, init_args, patch, scope, name)

	def trigger(self):
		if self.dest_obj is None:
			self.dest_obj = MFPApp().resolve(self.dest_name)

		if self.dest_obj is not None:
			self.dest_obj.send(self.inlets[0], inlet=self.dest_inlet)

class Recv (Processor):
	def __init__(self, init_type, init_args, patch, scope, name):
		initargs, kwargs = self.parse_args(init_args)
		Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
		self.bind(initargs[0])

	def trigger(self):
		self.outlets[0] = self.inlets[0]

def register():
	MFPApp().register("send", Send)
	MFPApp().register("recv", Recv)
