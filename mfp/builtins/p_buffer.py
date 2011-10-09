#! /usr/bin/env python
'''
p_buffer.py:  Builtin POSIX shared memory buffer

Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from mfp.main import MFPApp

class BufferInfo(object):
	def __init__(self, buf_id, size, channels):
		self.buf_id = buf_id
		self.size = size
		self.channels = channels

class Buffer(Processor):
	def __init__(self, init_type, init_args):

		initargs = self.parse_args(init_args)
		if len(initargs):
			size = initargs[0]
		if len(initargs) > 1:
			channels = initargs[1]
		else:
			channels = 1

		Processor.__init__(self, channels, 1, init_type, init_args)
		
		self.buf_id = None
		self.channels = 0
		self.size = 0
		self.shm_obj = None 

		self.dsp_inlets = list(range(channels)) 
		self.dsp_outlets = [0]
		self.dsp_init("buffer", size=size, channels=channels)

	def trigger(self):
		if self.inlets[0] is Bang:
			self.buf_id = self.dsp_obj.getparam("buf_id")
			self.channels = self.dsp_obj.getparam("channels")
			self.size = self.dsp_obj.getparam("size")

			self.outlets[0] = BufferInfo(self.buf_id, self.size, self.channels)
	
	def slice(self, start, end, channel=0):
		if self.shm_obj is None:
			self.shm_obj = SharedMemory(self.buf_id)

		try:
			os.lseek(self.shm_obj.fd, self.offset(channel, start), os.SEEK_SET)
			slc = os.read(self.shm_obj.fd, (end-start)*self.FLOAT_SIZE)
		except Exception, e:
			return None


def register():
	MFPApp().register("osc~", Osc)

