#! /usr/bin/env python2.6
'''
input_mode.py: InputMode parent class for managing key/mouse bindings and interaction

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

class InputMode (object):
	def __init__(self, description=''):
		self.description = description
		self.default = None 
		self.bindings = {} 

	def bind(self, keysym, action, helptext):
		self.bindings[keysym] = (action, helptext)

	def lookup(self, keysym):
		binding = self.bindings.get(keysym)
		if binding is None and self.default is not None:
			return (lambda: self.default(keysym), "default-key-handler")
		else:
			return binding

	def close(self):
		pass 
	
