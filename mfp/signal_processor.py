#! /usr/bin/env python2.6
'''
signal_processor.py: Parent class of DSP processors (Python side)

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from main import MFPApp

class SignalProcessor (object):
	def __init__(self, proc_name, inlets, outlets, ** params):
		self.dsp_obj = None 
		self.message("create", name=proc_name, inlets=inlets, outlets=outlets, params=params)

	def response(self, request):
		if request.payload.get("cmd") == "create":
			self.dsp_obj = request.response.get("obj_id")

	def message(self, cmd, callback=self.response, **args):
		payload = dict(cmd=cmd, args=args)
		MFPApp.dsp_message(payload, callback=self.response)

	def connect(self, outlet, target, inlet):
		self.message("connect", obj_id=self.dsp_obj, target=target.dsp_obj, 
			         outlet=outlet, inlet=inlet) 

	def disconnect(self, outlet, target, inlet):
		self.message("disconnect", obj_id=self.dsp_obj, target=target.dsp_obj, 
			         outlet=outlet, inlet=inlet) 
		
	def set_param(self, name, value):
		self.message("set_param", obj_id=self.dsp_obj, name=name, value=value)

	def get_param(self, name, callback=None):
		self.message("get_param", callback=callback, obj_id=self.dsp_obj, name=name) 


