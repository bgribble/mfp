#! /usr/bin/env python2.6
'''
p_plot.py: Stub for graphical plot I/O

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from datetime import datetime 
from ..processor import Processor 
from ..main import MFPApp
from .. import Bang, Uninit 

class Plot (Processor):
	def __init__(self, init_type, init_args):
		self.points = {}
		self.time_base = None

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
		from datetime import datetime
		if self.time_base is None:
			return 0
		return (datetime.now() - self.time_base).total_seconds()

	def _chartconf(self, action, data=None):
		self.gui_params['_chart_action'] = action
		self.gui_params['_chart_data'] = data

		MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)
		del self.gui_params['_chart_action']
		del self.gui_params['_chart_data']
		return True 
	
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
	def roll(self, *args, **kwargs):
		'''Start the plot roll function.'''
		if self.time_base is None:
			self.time_base = datetime.now()
		return self._chartconf('roll', self._time())

	def stop(self, *args, **kwargs):
		'''Stop the plot roll'''
		return self._chartconf('stop', self._time())

	def reset(self, *args, **kwargs):
		'''Reset time base for items with no X'''
		self.time_base = datetime.now()
		return self._chartconf('reset', self.time_base)

	def clearall(self, *args, **kwargs):
		'''Clear all data points'''
		self.points = {}
		return self._chartconf('clear')

	def clear(self, inlet=0):
		'''Clear a single curve's points'''
		if inlet is not None and self.points.has_key(inlet):
			del self.points[inlet]
		return self._chartconf('clear', inlet)

	def style(self, **kwargs):
		'''Set style parameters for a curve'''
		inlet = kwargs.get('inlet', 0)
		style = self.gui_params.setdefault('style', {})
		instyle = style.setdefault(inlet, {})
		for k, v in kwargs.items():
			if k != 'inlet':
				instyle[k] = v

		MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)
		return True 

	def bounds(self, x_min, y_min, x_max, y_max):
		'''Set viewport boundaries in plot coordinates'''
		return self._chartconf('bounds', (x_min, y_min, x_max, y_max))


def register():
	MFPApp().register("plot", Plot)
