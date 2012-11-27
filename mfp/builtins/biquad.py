#! /usr/bin/env python2.6
'''
biquad.py: Biquad filter implementation 

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from mfp.main import MFPApp
from mfp import log 

class Biquad(Processor):
	def __init__(self, init_type, init_args):
		Processor.__init__(self, 1, 1, init_type, init_args)
		initargs, kwargs = self.parse_args(init_args)

		self.dsp_inlets = [ 0 ]
		self.dsp_outlets = [ 0 ]
		self.dsp_init("biquad~")
	
	def trigger(self):
		if isinstance(self.inlets[0], dict):
			for param, val in self.inlets[0].items():
				try:
					self.dsp_setparam(param, float(val))
				except Exception, e:
					log.debug("biquad~: Error setting param", param, "to", type(val), str(val)) 
					log.debug("biquad~: Exception:", str(e))

def register():
	MFPApp().register("biquad~", Biquad)

