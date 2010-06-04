#! /usr/bin/env python2.6
'''
cp_var.py
Variable holder 
'''
import mfp
from ..control_processor import ControlProcessor 

class CPVar (ControlProcessor):
	def __init__(self, initval=None):
		self.value = initval
		ControlProcessor.__init__(self, inlets=2, outlets=1)

	def trigger(self):
		if self.inlets[1] is not None:
			self.value = self.inlets[1] 

		if isinstance(self.inlets[0], mfp.Bang):
			self.outlets[0] = self.value
		else:
			self.value = self.inlets[0]
			self.outlets[0] = self.value	

		self.propagate()

def register():
	from ..main import MFPApp
	MFPApp.register("var", CPVar)
