#! /usr/bin/env python2.6
'''
audio.py:  Builtin AudioOut/AudioIn DSP objects

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from mfp.main import MFPApp

class AudioOut(Processor):
	def __init__(self, init_type, init_args, patch, scope, name):
		Processor.__init__(self, 1, 0, init_type, init_args, patch, scope, name)
		initargs, kwargs = self.parse_args(init_args)

		if len(initargs):
			channel = initargs[0]
		else:
			channel = 0

		self.dsp_inlets = [0]
		self.dsp_init("out~")
		self.dsp_obj.setparam("channel", channel)
		

	def trigger(self):
		try:
			channel = int(self.inlets[0])
			self.dsp_obj.setparam("channel", channel)
		except:
			print "Can't convert %s to a channel number" % self.inlet[0]
				
class AudioIn(Processor):
	def __init__(self, init_type, init_args, patch, scope, name):
		Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
		initargs, kwargs = self.parse_args(init_args)

		if len(initargs):
			channel = initargs[0]
		else:
			channel = 0

		self.dsp_outlets = [0]
		self.dsp_init("in~")
		self.dsp_obj.setparam("channel", channel)


	def trigger(self):
		try:
			channel = int(self.inlets[0])
			self.set_param("channel", channel)
		except:
			print "Can't convert %s to a channel number" % self.inlet[0]
				

def register():
	MFPApp().register("in~", AudioIn)
	MFPApp().register("out~", AudioOut)


