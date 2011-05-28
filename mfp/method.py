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

	def call(self, target):
		try:
			m = getattr(target, self.method)
			if callable(m):
				print target, self.args, self.kwargs
				return m(*self.args, **self.kwargs)
			else:
				print "MethodCall.call():", target, self.method, m, type(m)
				raise Exception("Method %s cannot be called" % self.method)
		except AttributeError, e:
			raise Exception("Method %s not found for %s" % (self.method, target))


