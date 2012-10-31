
#! /usr/bin/env python2.6
'''
p_ampl.py:  Detector (peak/rms)

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from mfp.main import MFPApp

class Ampl(Processor):
	def __init__(self, init_type, init_args):
		Processor.__init__(self, 1, 2, init_type, init_args)
		initargs, kwargs = self.parse_args(init_args)

		self.dsp_inlets = [ 0 ]
		self.dsp_outlets = [0, 1]
		self.dsp_init("ampl")
	

def register():
	MFPApp().register("ampl~", Ampl)

