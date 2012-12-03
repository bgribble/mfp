#! /usr/bin/env python2.6 
'''
p_listops.py: Wrappers for common list operations

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor 
from ..main import MFPApp
from ..evaluator import Evaluator
from ..method import MethodCall
from ..bang import Bang, Uninit

class Collect (Processor):
	def __init__(self, init_type, init_args, patch, scope, name):
		initargs, kwargs = self.parse_args(init_args)
		if len(initargs):
			num_inlets = initargs[0]
		else:
			num_inlets = 1

		Processor.__init__(self, num_inlets, 1, init_type, init_args, patch, scope, name)

	def trigger(self):
		self.outlets[0] = self.inlets

def list_car(ll):
	return ll[0]

def list_cdr(ll):
	return ll[1:]

def register():
	MFPApp().register("collect", Collect)
