#! /usr/bin/env python
'''
cp_metro.py: Metronome control processor

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..timer import MultiTimer 
from ..control_processor import ControlProcessor
from ..main import MFPApp 
from ..datetime import datetime, timedelta 

class CPMetro (ControlProcessor): 
	_timer = None 

	def __init__(self, *initargs):
		self.started = False 
		self.interval = False 
		self.count = 0
		
		if CPMetro._timer is None:
			CPMetro._timer = MultiTimer()
			CPMetro._timer.start()

		if len(initargs):
			self.interval = int(initargs[0])

		ControlProcessor.__init__(self, inlets=2, outlets=1)


	def trigger(self):
		if self.inlets[1] is not None:
			self.interval = timedelta(milliseconds=int(self.inlets[1]))

		if self.inlets[0]:
			self.started = datetime.now()
			self.count = 1
			self._timer.schedule(self.started + self.interval, self.timer_cb)
			self.outlets[0] = True 
		else:
			self.started = False 

		self.propagate()

	def timer_cb(self):
		if self.started:
			self.outlets[0] = True
			self.count += 1 
			self._timer.schedule(self.started + self.count*self.interval, self.timer_cb)
			self.propagate()

def register():
	MFPApp.register("metro", CPMetro)
