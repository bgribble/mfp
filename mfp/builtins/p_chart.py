#! /usr/bin/env python2.6
'''
p_chart.py: Stub for graphical chart I/O

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor 
from ..main import MFPApp
from .. import Bang, Uninit 

class Chart (Processor):
	def __init__(self, init_type, init_args):
		self.points = []
		initargs, kwargs = self.parse_args(init_args)
		if len(initargs) > 0:
			chsannels = initargs[0]
		else: 
			channels = 1
		Processor.__init__(self, channels, 1, init_type, init_args)

	def trigger(self):
		if isinstance(self.inlets[0], (tuple, list)):
			self.points.append(tuple(self.inlets[0]))
			self.gui_params['_chart_action'] = 'add'
			self.gui_params['_chart_data'] = self.inlets[0]
			MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)
		else:
			pass
		self.inlets[0] = Uninit

	def clear(self):
		self.points = []
		self.gui_params['_chart_action'] = 'clear'
		if self.gui_params.has_key('_chart_data'):
			del self.gui_params['_chart_data']

		MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)

def register():
	MFPApp().register("chart", Chart)
