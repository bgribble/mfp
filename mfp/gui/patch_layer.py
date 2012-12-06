#! /usr/bin/env python
'''
patch_layer.py
A layer in the patch window 
'''

from gi.repository import Clutter
from mfp import log 

class PatchLayer(object):
	def __init__(self, stage, patch, name, scope=None):
		self.stage = stage
		self.patch = patch 
		self.name = name 
		self.scope = scope

		self.group = Clutter.Group() 
		self.group.set_property("opacity", 0)
		self.stage.group.add_actor(self.group)

	def show(self): 
		self.group.set_property("opacity", 255) 

	def hide(self):
		self.group.set_property("opacity", 0)

	
