#! /usr/bin/env python2.7
'''
midi.py: MIDI handling for MFP 

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import alsaseq
from threading import Thread
from datetime import datetime 

class MFPMidiManager(Thread): 
	def __init__(self, inports, outports):
		self.num_inports = inports
		self.num_outports = outports
		self.start_time = None 
		self.handlers = {} 

		self.quitreq = False 	

	def register(self, callback, ports):
		for p in ports: 
			hh = self.handlers.setdefault(p, [])
			hh.append(callback)

	def start(self):
		alsaseq.client('MFP', self.num_inports, self.num_outports, True)
		self.start_time = datetime.now()
		alsaseq.start()

		while not self.quitreq:
			events = alsaseq.input()
			print events 
	
	def send(self, port, data):
		pass
