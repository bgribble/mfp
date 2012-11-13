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
		from midi import NoteOn, NoteOff
		gg = globals()
		self.globals = { 
			'MethodCall': gg.get('MethodCall'),
			'Bang': gg.get('Bang'), 
			'NoteOn': NoteOn, 
			'NoteOff': NoteOff 
		}


	def eval_arglist(self, evalstr, extra_bindings=None):
		return self.eval(evalstr, extra_bindings, True)

	def eval(self, evalstr, extra_bindings=None, collect=False):
		def _eval_collect_args(*args, **kwargs):
			return (args, kwargs)

		if extra_bindings is None:
			extra_bindings = {}

		str2eval = evalstr.strip()
		if not len(str2eval):
			return None

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
		if len(tokens) > 2 and tokens[1][1] == '=':
			str2eval = ''.join(["dict("] + [t[1] for t in tokens] + [')']) 

		if collect:
			str2eval = "_eval_collect_args(%s)" % str2eval
			extra_bindings[ '_eval_collect_args' ] = _eval_collect_args 

		return eval(str2eval, self.globals, extra_bindings)

