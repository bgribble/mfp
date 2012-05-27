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
		self.points = {}
		initargs, kwargs = self.parse_args(init_args)
		if len(initargs) > 0:
			channels = initargs[0]
		else: 
			channels = 1
		self.hot_inlets = range(channels)
		Processor.__init__(self, channels, 1, init_type, init_args)

	def trigger(self):
		points = {}
		for i, val in zip(range(len(self.inlets)), self.inlets):
			if isinstance(val, (tuple, list)):
				v = tuple(val)
				cpts = self.points.setdefault(i, [])
				cpts.append(v)
				cpts = points.setdefault(i, [])
				cpts.append(v)
			else:
				pass
			self.inlets[i] = Uninit

		if points != {}:
			self.gui_params['_chart_action'] = 'add'
			self.gui_params['_chart_data'] = points
			MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)

	def clear(self, curve=None):
		if curve is None:
			self.points = {}
		elif curve is not None and self.points.has_key(curve):
			del self.points[curve]

		self.gui_params['_chart_action'] = 'clear'
		self.gui_params['_chart_data'] = curve

		MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)

def register():
	MFPApp().register("chart", Chart)
