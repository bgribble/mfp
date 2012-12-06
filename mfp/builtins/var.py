#! /usr/bin/env python2.6
'''
p_var.py: Variable holder 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor 
from ..main import MFPApp
from .. import Bang, Uninit 
from mfp import log 

class Var (Processor):
	'''
	Processor that holds a single Python value 

	Used as the backend for several different GUI elements, 
	slightly different behaviors, created with the appropriate name: 
		[message], [text], [var], [slider], [enum], [slidemeter]
	'''

	def __init__(self, init_type, init_args, patch, scope, name):
		self.gui_type = init_type 

		Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
		initargs, kwargs = self.parse_args(init_args)
		
		self.value = None 

		if self.init_type == "message":
			self.hot_inlets = (0,1)

		if len(initargs):
			self.value = initargs[0]
		elif len(kwargs):
			self.value = kwargs 

	def trigger(self):
		'''
		[var] trigger, basic form: 
			- on inlet 1, save value but do not output.
			  Possibly update GUI display. 
			- Bang on inlet 0: output stored value 
			- anything else on inlet 0: save and output value 
			  Possibly update GUI display 

		As [message]:
			- don't save value on inlet 0

		As [text]: 
			- ensure that value is a string and save it in the gui_params  

		'''
		do_update = False
		if self.inlets[1] is not Uninit:
			self.value = self.inlets[1] 
			if self.init_type == "text":
				self.value = str(self.value)
			self.inlets[1] = Uninit
			do_update = True

		if self.inlets[0] is not Uninit:
			# messages only change content on inlet 1, and Bang just 
			# causes output 
			if (self.init_type != "message") and (self.inlets[0] is not Bang):
				self.value = self.inlets[0]
				if self.init_type == "text":
					self.value = str(self.value)
				do_update = True 
			self.outlets[0] = self.value
			self.inlets[0] = Uninit

		if do_update and self.gui_created and self.gui_params.get("update_required"):
			self.gui_params['value'] = self.value

			if self.gui_created: 
				MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)

	def conf(self, **kwargs):
		for k, v in kwargs.items():
			self.gui_params[k] = v
			if self.gui_created and self.gui_params.get("update_required"):
				MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)

	def save(self):
		base_dict = Processor.save(self)
		base_dict["value"] = self.value 
		return base_dict 

	def load(self, params):
		if params.get("value"):
			self.value = params.get("value")
			if self.gui_params.get("value") is None:
				self.gui_params["value"] = self.value
		elif params.get("gui_params").get("value"):
			self.value = params.get("gui_params").get("value")

def register():
	MFPApp().register("var", Var)
	MFPApp().register("message", Var)
	MFPApp().register("text", Var)
	MFPApp().register("enum", Var)

