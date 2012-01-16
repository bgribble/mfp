#! /usr/bin/env python2.7
'''
osc.py: OSC server for MFP 

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import liblo

class MFPOscManager(Thread):
	def __init__(self, port):
		self.port = port 
		self.quitreq = False 

		try:
			self.server = liblo.server(self.port)
		except Exception, err:
			print str(err)
		
		self.server.add(None, None, self.default)

	def add_method(self, path, args, handler):
		pass

	def default(self, path, args, types, src):
		print path, args, types, src

	def run(self):
		while not self.quitreq:
			self.server.recv()

