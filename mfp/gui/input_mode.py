#! /usr/bin/env python2.6
'''
input_mode.py: InputMode parent class for managing key/mouse bindings and interaction

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from mfp import log 

class InputMode (object):
	def __init__(self, description=''):
		self.description = description
		self.default = None 
		self.bindings = {} 
		self.extensions = [] 

	def extend(self, mode):
		self.extensions.append(mode)
	
	def bind(self, keysym, action, helptext):
		self.bindings[keysym] = (action, helptext)

	def lookup(self, keysym):
		# first check our direct bindings 
		binding = self.bindings.get(keysym)
		if binding is not None:
			return binding 
		
		# if any extensions are specified, look in them 
		# (but don't use extension defaults)
		for ext in self.extensions: 
			binding = ext.bindings.get(keysym)
			if binding is not None:
				return binding 

		# do we have a default? 
		if self.default is not None:
			return (lambda: self.default(keysym), "default-key-handler")

		# do extensions have a default: 
		for ext in self.extensions: 
			if ext.default is not None:
				return (lambda: ext.default(keysym), "default-key-handler")

		return None 

	def close(self):
		pass 

	def __repr__(self):
		return "<InputMode %s>" % self.description
	
