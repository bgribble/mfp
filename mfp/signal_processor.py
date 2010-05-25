#! /usr/bin/env python2.6
'''
signal_processor.py: Parent class of DSP processors (Python side)

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

class SignalProcessor (object):
	def __init__(self, proc_name, inlets, outlets, ** params):
		self.dsp_obj = None 

		cmd = dict(cmd="create", 
			       args=dict(name=proc_name, inlets=inlets, outlets=outlets, params=params))
		request = MFPApp.instance.dsp_message(cmd)
		response = request.wait()
		if response.get('status', False):
			self.dsp_obj = response.get('obj_id')
		
	def connect(self, outlet, target, inlet):
		cmd = dict(cmd="connect",
			       args=dict(obj_id=self.dsp_obj, target=target.dsp_obj, 
					         outlet=outlet, inlet=inlet))
		MFPApp.instance.dsp_message(cmd)

	def disconnect(self, outlet, target, inlet):
		cmd = dict(cmd="disconnect",
			       args=dict(obj_id=self.dsp_obj, target=target.dsp_obj, 
					         outlet=outlet, inlet=inlet))
		MFPApp.instance.dsp_message(cmd)

	
	def set_param(self, name, value):
		cmd = dict(cmd="set_param",
				   args=dict(obj_id=self.dsp_obj, name=name, value=value))
		MFPApp.instance.dsp_message(cmd)

	def get_param(self, name):
		cmd = dict(cmd="get_param",
				   args=dict(obj_id=self.dsp_obj, name=name))
		request = MFPApp.instance.dsp_message(cmd)
		response = request.wait()
		if response.get('status', False):
			return response.get('value')


