#! /usr/bin/env python
'''
interpreter.py
Implement a wrapped-up InteractiveInterpreter subclass for use in 
the GUI or text-mode console 
'''

from .evaluator import Evaluator 
from code import InteractiveInterpreter 
from mfp import log 

class Interpreter (InteractiveInterpreter):
	def __init__(self, write_cb, local):
		self.write_cb = write_cb
		self.evaluator = Evaluator()
		self.local = local
		InteractiveInterpreter.__init__(self, local)

	def runsource(self, source, filename="<MFP interactive console>", symbol="single"):
	
		try:
			code = self.compile(source, filename, symbol)
		except (OverflowError, SyntaxError, ValueError):
			# Case 1
			self.showsyntaxerror(filename)
			return False

		if code is None:
			# Case 2
			return True

		if not len(source.strip()):
			self.write('')
		else:
			try:
				result = self.evaluator.eval(source, self.local)
				self.write(repr(result) + "\n")
			except SystemExit:
				raise
			except:
				self.showtraceback()

		return False 

	def write(self, msg): 
		self.write_cb(msg)

	

