#! /usr/bin/env python
'''
scopeplot.py 
Specialization of XYPlot for displaying waveform data from 
buffers 

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from .xyplot import XYPlot 
from mfp import log 
from posix_ipc import SharedMemory

class ScopePlot (XYPlot):
	def __init__(self, width, height):
		self.buf_info = None 
		self.shm_obj = None 
		self.data = [] 

		XYPlot.__init__(self, width, height) 

	def draw_field_cb(self, texture, ctxt, px_min, px_max):
		pass 

	def configure(self, params):
		pass

	def _grab(self):
		def offset(channel):
			return channel*self.size*self.FLOAT_SIZE

		if self.buf_info is None:
			return None 

		if self.shm_obj is None:
			self.shm_obj = SharedMemory(self.buf_info.buf_id)

		self.data = []

		try:
			for c in range(self.buf_info.channels):
				os.lseek(self.shm_obj.fd, offset(c), os.SEEK_SET)
				slc = os.read(self.shm_obj.fd, self.buf_info.size*self.FLOAT_SIZE)
				self.data.append(list(numpy.fromstring(slc, dtype=numpy.float32)))
		except Exception, e:
			log.debug("scopeplot: error grabbing data", e)
			return None

	def command(self, action, data):
		if action == "buffer": 
			log.debug("scopeplot: got buffer info", data)
			self.buffer = data  
		elif action == "grab":
			log.debug("scopeplot: grabbing data")
			self._grab() 
			self.plot.clear()





