#! /usr/bin/env python2.6 
'''
dsp_slave.py
Python main loop for DSP subprocess 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
import mfpdsp
from rpc_wrapper import RPCWrapper, rpcwrap

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
		return mfpdsp.proc_destroy(self.c_obj)

	@rpcwrap
	def getparam(self, param):
		return mfpdsp.proc_getparam(self.c_obj, param)
	
	@rpcwrap
	def setparam(self, param, value):
		return mfpdsp.proc_setparam(self.c_obj, param, value)

	@rpcwrap
	def connect(self, outlet, target, inlet):
		print "\ndsp_slave connect:", self.c_obj, outlet, type(outlet), DSPObject.objects.get(target), type(inlet)
		return mfpdsp.proc_connect(self.c_obj, outlet, DSPObject.objects.get(target), 
							       inlet)

	@rpcwrap
	def disconnect(self, outlet, target, inlet):
		return mfpdsp.proc_disconnect(self.c_obj, outlet, DSPObject.objects.get(target), 
								      inlet)

def dsp_init(pipe):
	DSPObject.pipe = pipe
	DSPObject.local = True

	pipe.on_finish(dsp_finish)

	# start JACK thread 
	mfpdsp.dsp_startup(1, 1)
	mfpdsp.dsp_enable()

def dsp_finish():
	mfpdsp.dsp_shutdown()

