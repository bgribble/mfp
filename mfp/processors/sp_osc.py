#! /usr/bin/env python2.6
'''
dsp_osc.py:  Builtin oscillator DSP objects

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from mfp.signal_processor import SignalProcessor 
from mfp.control_processor import ControlProcessor
from mfp.main import MFPApp

class SPOsc(SignalProcessor, ControlProcessor):
	def __init__(self, *initargs):
		if len(initargs):
			freq = initargs[0]
		else:
			freq = 0

		SignalProcessor.__init__(self, "osc~", 0, 1, freq=freq)
		ControlProcessor.__init__(self, 1, 0)


	def connect(self, outlet, target, inlet):
		return SignalProcessor.connect(self, outlet, target, inlet)

	def disconnect(self, outlet, target, inlet):
		return SignalProcessor.disconnect(self, outlet, target, inlet)

	def trigger(self):
		if self.inlets[0] is None:
			self.set_param("reset", True)
		else:
			try:
				freq = float(self.inlets[0])
				self.set_param("freq", self.inlets[0])
			except:
				print "Can't convert %s to a frequency value" % self.inlet[0]
				

def register():
	MFPApp.register("osc~", SPOsc)

