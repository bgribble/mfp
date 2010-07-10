#! /usr/bin/env python2.6
'''
p_arith.py:  Builtin arithmetic DSP ops

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from mfp.signal_processor import SignalProcessor 
from mfp.processor import Processor
from mfp.main import MFPApp

class Plus(Processor):
	def __init__(self, *initargs):
		Processor.__init__(self, inlets=2, outlets=1)

		if len(initargs):
			init_const = initargs[0]
		else:
			init_const = 0
		
		self.dsp_inlets = [0, 1]
		self.dsp_outlets = [0]
		self.dsp_init("+~")
		self.dsp_setparam("const", init_const)
		

	def trigger(self):
		try:
			val = float(self.inlets[0])
			self.dsp_setparam("const", val)
		except:
			print "Can't convert %s to a value" % self.inlet[0]
				

def register():
	MFPApp.register("+~", Plus)

