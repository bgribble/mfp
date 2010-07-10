#! /usr/bin/env python2.6 
'''
processor.py: Parent class of all processors 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from main import MFPApp 

class Processor (object): 
	def __init__(self, inlets, outlets):
		self.inlets = [None] * inlets
		self.outlets = [None] * outlets

		# dsp_inlets and dsp_outlets are the processor inlet/outlet numbers 
		# of the ordinal inlets/outlets of the DSP object. 
		# for example dsp_outlets = [2] means processor outlet 2 
		# corresponds to outlet 0 of the underlying DSP object 
		self.dsp_obj = None 
		self.dsp_inlets = []
		self.dsp_outlets = [] 

		self.connections = [[] for r in range(outlets)]
	
	def resize(self, inlets, outlets):
		if inlets > len(self.inlets):
			self.inlets += [None] * inlets-len(self.inlets)
		else:
			self.inlets[inlets:] = []

		if outlets > len(self.outlets):
			self.outlets += [None] * outlets-len(self.outlets)
			self.connections += [[] for r in range(outlets-len(self.outlets)) ]
		else:
			self.outlets[outlets:] = []
			self.connections[outlets:] = []

	def connect(self, outlet, target, inlet):
		# is this a DSP connection? 
		if outlet in self.dsp_outlets:
			self.dsp_connect(outlet, target, inlet)

		existing = self.connections[outlet]
		if (target,inlet) not in existing:
			existing.append((target,inlet))
		return True
	
	def disconnect(self, outlet, target, inlet):
		# is this a DSP connection? 
		if outlet in self.dsp_outlets:
			self.dsp_disconnect(outlet, target, inlet)

		existing = self.connections[outlet]
		if (target,inlet) in existing:
			existing.remove((target,inlet))
		return True


	def send(self, value, inlet=0):
		self.inlets[inlet] = value
		if inlet == 0:
			try:
				self.outlets = [None] * len(self.outlets)
				self.trigger()
			except: 
				import traceback
				tb = traceback.format_exc()
				self.error(tb)

	def error(self, tb=None):
		print "Error:", self
		if tb:
			print tb

	def propagate(self): 
		for conns, val in zip(self.connections, self.outlets):
			if val is not None:
				for target, inlet in conns:
					target.send(val, inlet)
	# 
	# DSP methods 
	# 

	def dsp_init(self, proc_name):
		self.dsp_obj = None 
		req = self.dsp_message("create", name=proc_name, inlets=len(self.dsp_inlets), 
					           outlets=len(self.dsp_outlets))
		MFPApp.wait(req)

	def dsp_response(self, request):
		if request.payload.get("cmd") == "create":
			self.dsp_obj = request.response

	def dsp_message(self, cmd, callback=None, **args):
		if callback is None:
			callback = self.dsp_response 
		payload = dict(cmd=cmd, args=args)
		return MFPApp.dsp_message(payload, callback=callback)

	def dsp_connect(self, outlet, target, inlet):
		self.dsp_message("connect", obj_id=self.dsp_obj, target=target.dsp_obj, 
			             outlet=self.dsp_outlets.index(outlet), 
				         inlet=target.dsp_inlets.index(inlet)) 
		return True

	def dsp_disconnect(self, outlet, target, inlet):
		self.dsp_message("disconnect", obj_id=self.dsp_obj, target=target.dsp_obj, 
			             outlet=self.dsp_outlets.index(outlet), 
				         inlet=target.dsp_inlets.index(inlet)) 
		
	def dsp_setparam(self, name, value):
		self.dsp_message("set_param", obj_id=self.dsp_obj, name=name, value=value)

	def dsp_getparam(self, name, callback=None):
		req = self.dsp_message("get_param", callback=callback, obj_id=self.dsp_obj, name=name) 
		MFPApp.wait(req)
		return req.response 

