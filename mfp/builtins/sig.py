#! /usr/bin/env python2.6
'''
p_sig.py:  Builtin constant signal 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp

class Sig(Processor):
	def __init__(self, init_type, init_args, patch, scope, name):
		Processor.__init__(self, 1, 0, init_type, init_args, patch, scope, name)

		initargs, kwargs = self.parse(init_args)
		if len(initargs):
			value = initargs[0]
		else:
			value = 0

		self.dsp_outlets=[0]
		self.dsp_init("sig~")
		self.dsp_obj.setparam("value", value)


	def trigger(self):
		try:
			val = float(self.inlets[0])
			self.dsp_obj.setparam("value", val)
		except:
			print "Can't convert %s to a value" % self.inlet[0]
				

def register():
	MFPApp().register("sig~", Sig)

