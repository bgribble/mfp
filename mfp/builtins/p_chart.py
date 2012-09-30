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

	def method(self, message, inlet):
		# magic inlet argument makes messages simpler
		if inlet != 0:
			message.kwargs['inlet'] = inlet
		message.call(self)

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
			self.finish_action()

	def clearall(self, **kwargs):
		self.points = {}

		self.gui_params['_chart_action'] = 'clear'
		self.gui_params['_chart_data'] = None

		MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)
		self.finish_action()

	def clear(self, inlet=0):
		if inlet is not None and self.points.has_key(inlet):
			del self.points[inlet]

		self.gui_params['_chart_action'] = 'clear'
		self.gui_params['_chart_data'] = inlet

		MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)
		self.finish_action()

	def style(self, **kwargs):
		inlet = kwargs.get('inlet', 0)
		style = self.gui_params.setdefault('style', {})
		instyle = style.setdefault(inlet, {})
		for k, v in kwargs.items():
			if k != 'inlet':
				instyle[k] = v

		MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)

	def bounds(self, x_min, y_min, x_max, y_max):
		self.gui_params['_chart_action'] = 'bounds'
		self.gui_params['_chart_data'] = (x_min, y_min, x_max, y_max)
		MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)
		self.finish_action()

	def finish_action(self):
		del self.gui_params['_chart_action']
		del self.gui_params['_chart_data']




def register():
	MFPApp().register("chart", Chart)
