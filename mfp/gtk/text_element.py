#! /usr/bin/env python2.6
'''
text_element.py
A text element (comment) in a patch
'''

import clutter 
from patch_element import PatchElement 

class TextElement (PatchElement):
	def __init__(self, window, x, y):
		PatchElement.__init__(self, window, x, y)
		self.text = ''
		self.editable = False
		self.actor = clutter.Text()

		# configure label
		self.actor.set_reactive(True)
		self.actor.set_color(window.color_unselected) 
		#self.actor.connect('text-changed', self.text_changed_cb)
		self.move(x, y)
		
		# add to stage 
		self.stage.stage.add(self.actor)
		
	def unselect(self, *args):
		self.actor.set_editable(False)
		self.actor.set_color(self.stage.color_unselected) 
		self.stage.stage.set_key_focus(None)
		self.text = self.actor.get_text()
		self.editable = False 

	def select(self, *args):
		self.actor.set_color(self.stage.color_selected) 

	def text_changed_cb(self, *args):
		print args

	def toggle_edit(self):
		if self.editable:
			self.actor.set_editable(False)
			self.editable = False 
		else:
			self.actor.set_editable(True)
			self.stage.stage.set_key_focus(self.actor)
			self.editable = True




