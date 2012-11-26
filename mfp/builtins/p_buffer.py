#! /usr/bin/env python
'''
p_buffer.py:  Builtin POSIX shared memory buffer

Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
'''

import numpy 
import os 
from mfp import Bang, Uninit
from mfp import log 

from mfp.processor import Processor
from mfp.main import MFPApp
from posix_ipc import SharedMemory

class BufferInfo(object):
	def __init__(self, buf_id, size, channels):
		self.buf_id = buf_id
		self.size = size
		self.channels = channels
	
	def __repr__(self):
		return "<buf_id=%s, chan_count=%d, chan_size=%d>" % (self.buf_id, self.channels, self.size)

class Buffer(Processor):
	
	RESP_TRIGGERED = 0
	RESP_BUFID = 1
	RESP_BUFSIZE = 2
	RESP_BUFCHAN = 3
	RESP_BUFRDY = 4

	FLOAT_SIZE = 4

	def __init__(self, init_type, init_args):

		initargs, kwargs = self.parse_args(init_args)
		if len(initargs):
			size = initargs[0]
		if len(initargs) > 1:
			channels = initargs[1]
		else:
			channels = 1

		Processor.__init__(self, channels, 3, init_type, init_args)
		
		self.buf_id = None
		self.channels = 0
		self.size = 0

		self.shm_obj = None 

		self.dsp_inlets = list(range(channels)) 
		self.dsp_outlets = [ 0 ]
		self.dsp_init("buffer", size=size, channels=channels)

	def offset(self, channel, start):
		return (channel*self.size + start)*self.FLOAT_SIZE

	def dsp_response(self, resp_id, resp_value):
		print "Buffer got response: %d %s\n" % (resp_id, resp_value)

		if resp_id == self.RESP_TRIGGERED:
			self.outlets[1] = resp_value
		elif resp_id == self.RESP_BUFID:
			if self.shm_obj:
				self.shm_obj.close_fd()
				self.shm_obj = None
			self.buf_id = resp_value
		elif resp_id == self.RESP_BUFSIZE:
			self.size = resp_value 
		elif resp_id == self.RESP_BUFCHAN:
			self.channels = resp_value 
		elif resp_id == self.RESP_BUFRDY:
			self.outlets[1] = BufferInfo(self.buf_id, self.size, self.channels)

	def trigger(self):
		incoming = self.inlets[0]
		if incoming is Bang:
			self.dsp_obj.setparam("trig_triggered", 1)
		elif incoming is True:
			self.dsp_obj.setparam("trig_enabled", 1)
		elif incoming is False:
			self.dsp_obj.setparam("trig_enabled", 0)
		elif isinstance(incoming, dict):
			for k, v in incoming.items():
				setattr(self, k, v)
				self.dsp_obj.setparam(k, v)
	
	def slice(self, start, end, channel=0):
		if self.shm_obj is None:
			self.shm_obj = SharedMemory(self.buf_id)

		try:
			os.lseek(self.shm_obj.fd, self.offset(channel, start), os.SEEK_SET)
			slc = os.read(self.shm_obj.fd, (end-start)*self.FLOAT_SIZE)
			self.outlets[2] = list(numpy.fromstring(slc, dtype=numpy.float32))
		except Exception, e:
			log.debug("buffer~: slice error '%s" % e) 
			return None

	def bufinfo(self):
		self.outlets[1] = BufferInfo(self.buf_id, self.size, self.channels)

def register():
	MFPApp().register("buffer~", Buffer)

