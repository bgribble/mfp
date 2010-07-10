#! /usr/bin/env python2.6 
'''
p_route.py: Route inputs to an output based on "address" in first element 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp
from .. import Bang 

class Route (Processor):
	'''
	[route 1, 2, 3, 4]

	[route] sends its input to one of its outputs, 
	where the output is determined by which of the creation args
	the input matches.  

	The route processor has n+1 outlets, where n is the number 
	of creation args.  The last outlet is for unmatched inputs. 
	'''
	def __init__(self, *addresses):
		self.addresses = {}  

		for addr, outlet in zip(addresses, range(len(addresses))):
			self.addresses[addr] = outlet 

		self.nomatch = len(addresses) 
		Processor.__init__(self, inlets=2, outlets=(len(addresses) + 1))

	def trigger(self):
		# inlet 1 resets the list of addresses and may change the number of 
		# outputs 
		if self.inlets[1] is not None:
			if len(self.inlets[1]) != self.nomatch:
				self.resize(2, len(self.inlets[1]) + 1)

			for addr, outlet in zip(self.inlets[1], range(len(self.inlets[1]))):
				self.addresses[addr] = outlet 
				self.nomatch = len(self.inlets[1])

			self.inlets[1] = None

		# hot inlet 
		if self.inlets[0] is not None:
			if isinstance(self.inlets[0], list) or isinstance(self.inlets[0], tuple):
				k = self.inlets[0][0]
				d = self.inlets[0][1:]
			else: 
				k = self.inlets[0]
				d = Bang

			outlet = self.addresses.get(k)
			if outlet is None:
				self.outlets[self.nomatch] = self.inlets[0]
			else: 
				self.outlets[outlet] = d

		self.propagate()
			
def register():
	MFPApp.register("route", Route)
