#! /usr/bin/env python2.6
'''
p_line.py:  Builtin line/ramp generator 

Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from mfp.main import MFPApp

class Line(Processor):
	def __init__(self, init_type, init_args):
		Processor.__init__(self, 1, 1, init_type, init_args)
		initargs = self.parse_args(init_args)

		segments = None
		if len(initargs):
			segments = initargs[0]

		self.dsp_outlets = [0]
		self.dsp_init("line", segments=segments)
	
	def trigger(self):
		if self.inlets[0] is not None:
			try:
				segs = self.inlets(0)
				tlen = len(segs)
				self.set_param("segments", segs)
			except:
				print "Error processing segment list for line~"

		if self.inlets[1] is not None:
			try:
				ff = float(self.inlets[1])
				self.set_param("position", ff)
			except:
				print "Error processing position for line~"

def register():
	MFPApp().register("line~", Line)

