#! /usr/bin/env python2.6 
'''
dsp.py
Python main loop for DSP subprocess 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
import mfpdsp
from rpc_wrapper import RPCWrapper, rpcwrap

class DSPCommand (RPCWrapper):
	def __init__(self):
		self.last_objid = 0
		self.objects = {}
		RPCWrapper.__init__(self)

	def remember(self, obj):
		oid = self.next_objid
		self.next_objid += 1
		self.objects[oid] = obj
		return oid

	def recall(self, oid):
		return self.objects.get(oid)

	@rpcwrap
	def create(self, name, inlets, outlets, params):
		obj = mfpdsp.proc_create(name, inlets, outlets, params)
		oid = self.remember(obj)
		return oid

	@rpcwrap
	def get_param(self, obj_id, param):
		obj = self.recall(obj_id)
		if obj:
			return mfpdsp.proc_getparam(obj, param)
	
	@rpcwrap
	def set_param(self, obj_id, param, value):
		obj = self.recall(obj_id)
		print "setparam:", obj, param, value
		if obj:
			return mfpdsp.proc_setparam(obj, param, value)
		else:
			return None

	@rpcwrap
	def connect(self, obj_id, outlet, target, inlet):
		src = self.recall(obj_id)
		dst = self.recall(target)
		return mfpdsp.proc_connect(src, outlet, dst, inlet)

	@rpcwrap
	def disconnect(self, obj_id, outlet, target, inlet):
		src = self.recall(obj_id)
		dst = self.recall(target)
		return mfpdsp.proc_disconnect(src, outlet, dst, inlet)

def dsp_init(pipe):
	DSPCommand.pipe = pipe
	DSPCommand.local = True

	pipe.on_finish(dsp_finish)

	# start JACK thread 
	mfpdsp.dsp_startup(1, 1)
	mfpdsp.dsp_enable()

def dsp_finish():
	mfpdsp.dsp_shutdown()
