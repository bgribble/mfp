#! /usr/bin/env python2.6
'''
p_var.py: Variable holder 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor 
from ..main import MFPApp
from .. import Bang, Uninit 

class Var (Processor):
	def __init__(self, init_type, init_args):
		Processor.__init__(self, 2, 1, init_type, init_args)
		initargs, kwargs = self.parse_args(init_args)
		if len(initargs):
			self.value = initargs[0]
		else:
			self.value = None

	def trigger(self):
		if self.inlets[1] is not Uninit:
			self.value = self.inlets[1] 
			self.inlets[1] = Uninit

		if self.inlets[0] is Bang:
			self.outlets[0] = self.value
		else:
			self.value = self.inlets[0]
			if self.gui_params.get("update_required"):
				print "p_var: configuring GUI"
				# FIXME what if no gui obj?
				self.gui_params['value'] = self.value
				MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)

			self.outlets[0] = self.value	

def register():
	MFPApp().register("var", Var)
	MFPApp().register("message", Var)
