#! /usr/bin/env python2.6
'''
method.py: MethodCall wrapper for passing messages to objects 

Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
'''

class MethodCall(object): 
	def __init__(self, method, *args, **kwargs):
		self.method = method
		self.args = args
		self.kwargs = kwargs
		self.fallback = None 

		try:
			from .evaluator import Evaluator
			ev = Evaluator()
			meth = ev.eval(self.method)
			if callable(meth):
				self.fallback = meth
		except:
			print "MethodCall: no global fallback for", self.method
			pass

	def call(self, target):
		try:
			m = getattr(target, self.method)
		except AttributeError, e:
			raise Exception("Method %s not found for %s" % (self.method, target))

		if callable(m):
			try: 
				return m(*self.args, **self.kwargs)
			except Exception, e:
				raise Exception("Method %s for %s raised exception %s" 
					            % (self.method, target, e))
		elif self.fallback:
			try: 
				return self.fallback([self] + self.args, **self.kwargs)
			except Exception, e:
				raise Exception("Method %s for %s raised exception %s" 
					            % (self.method, target, e))
		else:
			print "MethodCall.call():", target, self.method, m, type(m)
			raise Exception("Method %s cannot be called" % self.method)


