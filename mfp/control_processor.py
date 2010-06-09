#! /usr/bin/env python2.6 
'''
control_processor.py: Parent class of control-rate processors 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

class ControlProcessor (object): 
	
	def __init__(self, inlets, outlets):
		self.inlets = [None] * inlets
		self.outlets = [None] * outlets 
		self.connections = [[] for r in range(outlets)]

	def resize(self, inlets, outlets):
		if inlets > len(self.inlets):
			self.inlets += [None] * inlets-len(self.inlets)
		else:
			self.inlets[inlets:] = []

		if outlets > len(self.outlets):
			self.outlets += [None] * outlets-len(self.outlets)
			self.connections += [[] for r in range(outlets-len(self.outlets)) ]
		else:
			self.outlets[outlets:] = []
			self.connections[outlets:] = []

	def connect(self, outlet, target, inlet):
		existing = self.connections[outlet]
		if (target,inlet) not in existing:
			existing.append((target,inlet))
	
	def send(self, value, inlet=0):
		self.inlets[inlet] = value
		if inlet == 0:
			try:
				self.outlets = [None] * len(self.outlets)
				self.trigger()
			except: 
				import traceback
				tb = traceback.format_exc()
				self.error(tb)

	def error(self, tb=None):
		print "Error:", self
		if tb:
			print tb

	def propagate(self): 
		for conns, val in zip(self.connections, self.outlets):
			if val is not None:
				for target, inlet in conns:
					target.send(val, inlet)
	
