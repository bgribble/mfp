#! /usr/bin/env python
'''
p_metro.py: Metronome control processor

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..timer import MultiTimer 
from ..processor import Processor
from ..main import MFPApp 
from datetime import datetime, timedelta 
from .. import Bang

class MetroTick (object):
	pass

class Metro (Processor): 
	_timer = None 

	def __init__(self, *initargs):
		self.started = False 
		self.interval = False 
		self.count = 0
		
		if Metro._timer is None:
			Metro._timer = MultiTimer()
			Metro._timer.start()

		if len(initargs):
			self.interval = timedelta(milliseconds=int(initargs[0]))

		Processor.__init__(self, inlets=2, outlets=1)

	def trigger(self):
		if self.inlets[1] is not None:
			self.interval = timedelta(milliseconds=int(self.inlets[1]))
			self.inlets[1] = None 

		if isinstance(self.inlets[0], MetroTick) and self.started:
			self.outlets[0] = Bang 
			self.count += 1 
			self._timer.schedule(self.started + self.count*self.interval, self.timer_cb)
		if self.inlets[0] is Bang or self.inlets[0]:
			self.started = datetime.now()
			self.count = 1
			self._timer.schedule(self.started + self.interval, self.timer_cb)
			self.outlets[0] = Bang
		else:
			self.started = False 

	def timer_cb(self):
		self.send(MetroTick())

def register():
	MFPApp.register("metro", Metro)
