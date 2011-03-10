#! /usr/bin/env python2.6
'''
p_noise.py:  Builtin noise 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp

class Noise(Processor):
	def __init__(self, init_type, init_args):
		Processor.__init__(self, 0, 1, init_type, init_args)

		self.dsp_outlets=[0]
		self.dsp_init("noise")

	def trigger(self):
		pass	

def register():
	MFPApp().register("noise~", Noise)

