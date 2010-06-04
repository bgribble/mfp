
from ..control_processor import ControlProcessor 
from ..main import MFPApp

class CPPyBinary(ControlProcessor):
	def __init__(self, pyfunc, *initargs):
		self.function = pyfunc
		ControlProcessor.__init__(self, inlets=2, outlets=1)
		if len(initargs) == 1:
			self.inlets[1] = initargs[0]

	def trigger(self):
		self.outlets[0] = self.function(self.inlets[0], self.inlets[1])
		self.propagate()

class CPPyUnary(ControlProcessor):
	def __init__(self, pyfunc):
		self.function = pyfunc
		ControlProcessor.__init__(self, inlets=1, outlets=1)

	def trigger(self):
		self.outlets[0] = self.function(self.inlets[0])
		self.propagate()

def mk_binary(pyfunc, name):
	def factory(*args):
		proc = CPPyBinary(pyfunc, *args)
		return proc 
	MFPApp.register(name, factory)

def mk_unary(pyfunc, name):
	def factory(*args):
		proc = CPPyUnary(pyfunc, *args)
		return proc
	MFPApp.register(name, factory)

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



