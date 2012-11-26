#! /usr/bin/env python
'''
scopeplot.py 
Specialization of XYPlot for displaying waveform data from 
buffers 

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from .xyplot import XYPlot 
from mfp import log 

class ScopePlot (XYPlot):
	def __init__(self, width, height):
		self.buffer = None 

		XYPlot.__init__(self, width, height) 

	def draw_field_cb(self, texture, ctxt, px_min, px_max):
		pass 

	def configure(self, params):
		pass

	def command(self, action, data):
		if action == "buffer": 
			log.debug("scopeplot: got buffer info", data)
			self.buffer = data  



