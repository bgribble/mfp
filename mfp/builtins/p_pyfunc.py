#! /usr/bin/env python2.6 
'''
p_pyfunc.py: Wrappers for common unary and binary Python functions 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor 
from ..main import MFPApp

class PyBinary(Processor):
	def __init__(self, pyfunc, init_type, init_args):
		self.function = pyfunc
		Processor.__init__(self, 2, 1, init_type, init_args)
		initargs = self.parse_args(init_args)
		if len(initargs) == 1:
			self.inlets[1] = initargs[0]

	def trigger(self):
		print self.inlets[0], type(self.inlets[0]), self.inlets[1], type(self.inlets[1])
		self.outlets[0] = self.function(self.inlets[0], self.inlets[1])

class PyUnary(Processor):
	def __init__(self, pyfunc, init_type, init_args):
		self.function = pyfunc
		Processor.__init__(self, 1, 1, init_type, init_args)

	def trigger(self):
		self.outlets[0] = self.function(self.inlets[0])

def mk_binary(pyfunc, name):
	def factory(iname, args):
		proc = PyBinary(pyfunc, iname, args)
		return proc 
	MFPApp().register(name, factory)

def mk_unary(pyfunc, name):
	def factory(iname, args):
		proc = PyUnary(pyfunc, iname, args)
		return proc
	MFPApp().register(name, factory)

import operator, math

def register():
	mk_binary(operator.add, "+")
	mk_binary(operator.sub, "-")
	mk_binary(operator.mul, "*")
	mk_binary(operator.div, "/")
	mk_binary(operator.mod, "%")

	mk_unary(math.exp, "exp")
	mk_unary(math.log, "log")
	mk_binary(math.pow, "pow")

	mk_binary(operator.gt, ">")
	mk_binary(operator.lt, "<")
	mk_binary(operator.ge, ">=")
	mk_binary(operator.le, "<=")
	mk_binary(operator.eq, "==")
	mk_binary(operator.ne, "!=")

	mk_unary(abs, "abs")
	mk_unary(operator.neg, "neg")

	# type converters
	mk_unary(int, "int")
	mk_unary(float, "float")
	mk_unary(tuple, "tuple")
	mk_unary(list, "list")


