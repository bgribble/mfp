#! /usr/bin/env python
'''
p_route.py: Route inputs to an output based on "address" in first element 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp
from .. import Bang, Uninit 

class Route (Processor):
	'''
	[route 1, 2, int, float]
	[route= 1, 2, (3,1), 4]
	[case 1, 2, [3,4,5], 6]

	[route] takes as input a pair of (address, data) and routes the data part to one of its outputs,
	where the output is determined by which of the creation args the address matches.  

	[case] assumes that its input data is the address, and routes the data to the selected
	output unaltered.

	if multiple addresses match, the leftmost is used.

	Default behaviors, disabled when created as [route=] or [case=]: If the test arguments are type
	objects, they match if the input is that type.  If test args are lists, they match if the input
	matches any item in the list. 

	The route processor has n+1 outlets, where n is the number of creation args.  The last outlet is
	for unmatched inputs. 
	'''
	def __init__(self, init_type, init_args):
		if init_type[-1] == '=':
			self.strict = True
		else:
			self.strict = False

		if init_type[:4] == 'cond':
			self.addressed_data = False
		else:
			self.addressed_data = True

		self.addresses = {}  
		self.type_addresses = {}

		self._update_addresses(self.parse_args(init_args))

		Processor.__init__(self, 2, self.nomatch+1, init_type, init_args)

	def _update_addresses(self, values):
		self.addresses = {} 
		for addr, outlet in zip(values, range(len(values))):
			if not self.strict and isinstance(addr, type):
				self.type_addresses[addr] = outlet
			elif not self.strict and isinstance(addr, (list, tuple)):
				for a in addr:
					if isinstance(a, type):
						self.type_addresses[a] = outlet
					else:
						self.addresses[a] = outlet 
			else:
				self.addresses[addr] = outlet 
		self.nomatch = len(values)

	def trigger(self):
		print "route trigger:", self.inlets

		# inlet 1 resets the list of addresses and may change the number of 
		# outputs 
		if self.inlets[1] is not Uninit:
			print "resizing addresses", self.inlets[1]
			if len(self.inlets[1]) != self.nomatch:
				self.resize(2, len(self.inlets[1]) + 1)
			self._update_addresses(self.inlets[1])

			self.inlets[1] = Uninit 

		# hot inlet 
		if self.inlets[0] is not Uninit:
			print "Got hot input:", self.inlets[0]
			if self.addressed_data is False:
				k = self.inlet[0]
				d = k
			elif isinstance(self.inlets[0], list) or isinstance(self.inlets[0], tuple):
				k = self.inlets[0][0]
				d = self.inlets[0][1:]
			else: 
				k = self.inlets[0]
				d = Bang
			print "key:", k, "data:", d

			if self.strict:
				outlet = self.addresses.get(k)
			else:
				direct_addr = self.addresses.get(k)
				type_addr = None
				type_matches = [ self.type_addresses.get(t) for t in self.type_addresses.keys()
								  if isinstance(k, t) ]
				if type_matches:
					type_addr = min(type_matches)

				if direct_addr is None:
					outlet = type_addr
				elif type_addr is None:
					outlet = direct_addr
				else:
					outlet = min(direct_addr, type_addr)

			print "Found outlet", outlet 
			if outlet is None:
				self.outlets[self.nomatch] = self.inlets[0]
			else: 
				self.outlets[outlet] = d
			
def register():
	MFPApp().register("route", Route)
	MFPApp().register("route=", Route)
	MFPApp().register("case", Route)
	MFPApp().register("case=", Route)

