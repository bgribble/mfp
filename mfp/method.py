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
		m = target.__dict__.get(self.method)
		if callable(m):
			return m(target, *self.args, **self.kwargs)
		else:
			raise Exception("Method %s cannot be called" % self.method)

