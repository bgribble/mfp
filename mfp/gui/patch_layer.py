#! /usr/bin/env python
'''
patch_layer.py
A layer in the patch window 
'''

from gi.repository import Clutter
from mfp import log 

class PatchLayer(object):
	def __init__(self, patch, name):
		self.patch = patch 
		self.name = name 
		self.group = Clutter.Group() 
		self.group.set_property("opacity", 0)
		self.patch.group.add_actor(self.group)

	def show(self): 
		self.group.set_property("opacity", 255) 

	def hide(self):
		self.group.set_property("opacity", 0)

	
