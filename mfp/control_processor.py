#! /usr/bin/env python2.6 
'''
control_processor.py: Parent class of control-rate processors 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

class ControlProcessor (object): 
	
	def __init__(self, inlets, outlets):
		self.inlets = [None] * inlets
		self.outlets = [None] * outlets 
		self.connections = [[]] * outlets 

	def connect(self, outlet, target, inlet):
		existing = self.connections[outlet]
		if (target,inlet) not in existing:
			existing.append((target,inlet))
	
	def send(self, value, inlet=0):
		self.inlets[inlet] = value
		if inlet == 0:
			try:
				self.trigger()
			except: 
				self.error()

	def error(self):
		print "Error:", self

	def propagate(self): 
		for conns, val in zip(self.connections, self.outlets):
			if val is not None:
				for target, inlet in conns:
					target.send(val, inlet)

	
