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

	def _time(self):
		return (datetime.now() - self.time_base).total_seconds()

	def _chartconf(self, action, data=None):
		self.gui_params['_chart_action'] = action
		self.gui_params['_chart_data'] = data

		MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)
		del self.gui_params['_chart_action']
		del self.gui_params['_chart_data']
	
	def trigger(self):
		points = {}
		for i, val in zip(range(len(self.inlets)), self.inlets):
			v = None
			if isinstance(val, (tuple, list)):
				v = tuple(val)
			elif isinstance(val, (float, int)):
				v = (self._time(), val)

			if v is not None:
				cpts = self.points.setdefault(i, [])
				cpts.append(v)
				cpts = points.setdefault(i, [])
				cpts.append(v)
			self.inlets[i] = Uninit

		if points != {}:
			self._chartconf('add', points)

	# methods that the object responds to 
	def roll(self, **kwargs):
		'''Start the chart roll function.'''
		self._chartconf('roll', self._time())

	def stop(self, **kwargs):
		'''Stop the chart roll'''
		self._chartconf('stop', self._time())

	def reset(self, **kwargs):
		'''Reset time base for items with no X'''
		self.time_base = datetime.now()
		self._chartconf('reset', self.time_base)

	def clearall(self, **kwargs):
		'''Clear all data points'''
		self.points = {}
		self._chartconf('clear')

	def clear(self, inlet=0):
		'''Clear a single curve's points'''
		if inlet is not None and self.points.has_key(inlet):
			del self.points[inlet]
		self._chartconf('clear', inlet)

	def style(self, **kwargs):
		'''Set style parameters for a curve'''
		inlet = kwargs.get('inlet', 0)
		style = self.gui_params.setdefault('style', {})
		instyle = style.setdefault(inlet, {})
		for k, v in kwargs.items():
			if k != 'inlet':
				instyle[k] = v

		MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)

	def bounds(self, x_min, y_min, x_max, y_max):
		'''Set viewport boundaries in chart coordinates'''
		self._chartconf('bounds', (x_min, y_min, x_max, y_max))





def register():
	MFPApp().register("chart", Chart)
