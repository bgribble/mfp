#! /usr/bin/env python2.6 
'''
dsp_slave.py
Python main loop for DSP subprocess 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
import mfpdsp
from rpc_wrapper import RPCWrapper, rpcwrap

PROC_CONNECT = 1
PROC_DISCONNECT = 2
PROC_SETPARAM = 3
PROC_DELETE = 4

def dsp_config(*args):
	mfpdsp.dsp_get_cmdqueue().append(args)

class DSPObject(RPCWrapper):
	objects = {}
	def __init__(self, obj_id, name, inlets, outlets, params={}):
		print "DSPObject.__init__", self.local
		self.obj_id = obj_id 
		RPCWrapper.__init__(self, obj_id, name, inlets, outlets, params)
		if self.local:
			self.c_obj = mfpdsp.proc_create(name, inlets, outlets, params)
			DSPObject.objects[self.obj_id] = self.c_obj

	@rpcwrap
	def delete(self):
		dsp_config(PROC_DELETE, self.c_obj)

	@rpcwrap
	def getparam(self, param):
		return mfpdsp.proc_getparam(self.c_obj, param)
	
	@rpcwrap
	def setparam(self, param, value):
		return dsp_config(PROC_SETPARAM, self.c_obj, param, value)

	@rpcwrap
	def connect(self, outlet, target, inlet):
		dst = DSPObject.objects.get(target)
		return dsp_config(PROC_CONNECT, self.c_obj, outlet, dst, inlet)

	@rpcwrap
	def disconnect(self, outlet, target, inlet):
		dst = DSPObject.objects.get(target)
		return dsp_config(PROC_DISCONNECT, self.c_obj, outlet, dst, inlet)

def dsp_init(pipe):
	DSPObject.pipe = pipe
	DSPObject.local = True

	pipe.on_finish(dsp_finish)

	# start JACK thread 
	mfpdsp.dsp_startup(1, 1)
	mfpdsp.dsp_enable()

def dsp_finish():
	mfpdsp.dsp_shutdown()

