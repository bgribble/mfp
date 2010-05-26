
#! /usr/bin/env python2.6
'''
sp_dac.py:  Builtin DAC/ADC DSP objects

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from mfp.signal_processor import SignalProcessor 
from mfp.control_processor import ControlProcessor
from mfp.main import MFPApp

class SPDac(SignalProcessor, ControlProcessor):

	def __init__(self, *initargs):
		if len(initargs):
			channel = initargs[0]
		else:
			channel = 0

		SignalProcessor.__init__(self, "dac~", 1, 0, channel=channel)
		ControlProcessor.__init__(self, 1, 0)

	def connect(self, outlet, target, inlet):
		return False

	def disconnect(self, outlet, target, inlet):
		return False

	def trigger(self):
		try:
			channel = int(self.inlets[0])
			self.set_param("channel", channel)
		except:
			print "Can't convert %s to a channel number" % self.inlet[0]
				
class SPAdc(SignalProcessor, ControlProcessor):

	def __init__(self, *initargs):
		if len(initargs):
			channel = initargs[0]
		else:
			channel = 0

		SignalProcessor.__init__(self, "adc~", 0, 1, channel=channel)
		ControlProcessor.__init__(self, 1, 0)


	def connect(self, outlet, target, inlet):
		return SignalProcessor.connect(self, outlet, target, inlet)

	def disconnect(self, outlet, target, inlet):
		return SignalProcessor.disconnect(self, outlet, target, inlet)

	def trigger(self):
		try:
			channel = int(self.inlets[0])
			self.set_param("channel", channel)
		except:
			print "Can't convert %s to a channel number" % self.inlet[0]
				

def register():
	MFPApp.register("adc~", SPAdc)
	MFPApp.register("dac~", SPDac)


