#! /usr/bin/env python2.6
'''
evaluator.py:  Augmented Python eval for strings in user interface

Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
'''

import tokenize 
from StringIO import StringIO
from .method import MethodCall
from .bang import Bang

class Evaluator (object):
	def __init__(self):
		self._init_globals()

	def _init_globals(self):
		gg = globals()
		self.globals = { 
			'MethodCall': gg.get('MethodCall'),
			'Bang': gg.get('Bang')
		}

	def eval(self, evalstr, extra_bindings=None):
		str2eval = evalstr.strip()
		sio = StringIO(str2eval)

		tokens = [ t for t in tokenize.generate_tokens(sio.read) 
		           if t[1] != '']
		
		# Method call special form: 
		#   @method(arg1, arg2, ..., kwarg=val, kwarg2=val)
		# rewrites to: 
		#	MethodCall("method", arg1, arg2, ... kwarg=val, kwarg2=val
		# 
		# @foo is a synonym for @foo() 
		if tokens[0][1] == '@' and len(tokens) >= 2:
			methname = tokens[1][1]
			if len(tokens) == 2:
				str2eval = ''.join(["MethodCall(", '"', methname, '"', ')'])
			else:
				if tokens[2][1] != '(':
					raise SyntaxError()
				str2eval = ''.join(["MethodCall(", '"', methname, '",' ] 
									+ [ t[1] for t in tokens[3:]])
		# setparam special form:
		#   foo='bar', bax='baz'
		# rewrites to 
		#   dict(foo='bar', bax='baz')


		return eval(str2eval, self.globals)

