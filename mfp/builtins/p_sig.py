#! /usr/bin/env python2.6
'''
p_sig.py:  Builtin constant signal 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp

class Sig(Processor):
	def __init__(self, *initargs):
		Processor.__init__(self, inlets=1, outlets=0)

		if len(initargs):
			value = initargs[0]
		else:
			value = 0

		self.dsp_outlets=[0]
		self.dsp_init("sig~")
		self.dsp_setparam("value", value)


	def trigger(self):
		try:
			val = float(self.inlets[0])
			self.dsp_setparam("value", val)
		except:
			print "Can't convert %s to a value" % self.inlet[0]
				

def register():
	MFPApp.register("sig~", Sig)

