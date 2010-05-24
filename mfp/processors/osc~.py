#! /usr/bin/env python2.6
'''
dsp_osc.py:  Builtin oscillator DSP objects

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

class DSPOsc (SignalProcessor, ControlProcessor):
	def __init__(self, *initargs):
		if len(initargs):
			freq = initargs[0]
		else:
			freq = 0

		SignalProcessor.__init__(self, "osc~", 0, 1, freq=freq)
		ControlProcessor.__init__(self, 1, 0)

	def trigger(self):
		if self.inlets[0] is None:
			self.set_param("reset", True)
		else:
			try:
				freq = float(self.inlets[0])
				self.set_param("freq", self.inlets[0])
			except:
				print "Can't convert %s to a frequency value" % self.inlet[0]
				


