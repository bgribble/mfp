#! /usr/bin/env python2.6
'''
signal_processor.py: Parent class of DSP processors (Python side)

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from main import MFPApp

class SignalProcessor (object):
	def __init__(self, proc_name, inlets, outlets, ** params):
		self.dsp_obj = None 
		req = self.message("create", name=proc_name, inlets=inlets, 
					       outlets=outlets, params=params)
		MFPApp.wait(req)

	def response(self, request):
		if request.payload.get("cmd") == "create":
			self.dsp_obj = request.response

	def message(self, cmd, callback=None, **args):
		if callback is None:
			callback = self.response 
		payload = dict(cmd=cmd, args=args)
		return MFPApp.dsp_message(payload, callback=callback)

	def connect(self, outlet, target, inlet):
		self.message("connect", obj_id=self.dsp_obj, target=target.dsp_obj, 
			         outlet=outlet, inlet=inlet) 
		return True

	def disconnect(self, outlet, target, inlet):
		self.message("disconnect", obj_id=self.dsp_obj, target=target.dsp_obj, 
			         outlet=outlet, inlet=inlet) 
		
	def set_param(self, name, value):
		self.message("set_param", obj_id=self.dsp_obj, name=name, value=value)

	def get_param(self, name, callback=None):
		req = self.message("get_param", callback=callback, obj_id=self.dsp_obj, name=name) 
		MFPApp.wait(req)
		return req.response 

