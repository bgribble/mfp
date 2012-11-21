#! /usr/bin/env python
'''
scopeplot.py 
Specialization of XYPlot for displaying waveform data from 
buffers 

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from .xyplot import XYPlot 

class ScopePlot (XYPlot):
	def __init__(self, width, height):

		

		XYPlot.__init__(self, width, height) 

	def draw_field_cb(self, texture, ctxt, px_min, px_max):
		pass 

