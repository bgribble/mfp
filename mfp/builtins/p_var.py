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
	def __init__(self, init_type, init_args):
		Processor.__init__(self, 2, 1, init_type, init_args)
		initargs, kwargs = self.parse_args(init_args)
		
		self.value = None 

		if self.init_type == "message":
			self.hot_inlets = (0,1)

		if len(initargs):
			self.value = initargs[0]
		elif len(kwargs):
			self.value = kwargs 

	def trigger(self):
		do_update = False
		if self.inlets[1] is not Uninit:
			self.value = self.inlets[1] 
			self.inlets[1] = Uninit
			do_update = True

		if self.inlets[0] is not Uninit:
			if (self.init_type != "message") and (self.inlets[0] is not Bang):
				self.value = self.inlets[0]
				do_update = True 
			self.outlets[0] = self.value
			self.inlets[0] = Uninit

		if do_update and self.gui_params.get("update_required"):
			# FIXME what if no gui obj?
			self.gui_params['value'] = self.value
			MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)

	def conf(self, **kwargs):
		for k, v in kwargs.items():
			self.gui_params[k] = v
			if self.gui_params.get("update_required"):
				MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)


def register():
	MFPApp().register("var", Var)
	MFPApp().register("message", Var)
