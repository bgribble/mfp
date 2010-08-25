#! /usr/bin/env python2.6
'''
text_element.py
A text element (comment) in a patch
'''

import clutter 
from patch_element import PatchElement 
from mfp import MFPGUI

class TextElement (PatchElement):
	element_type = "text"

	def __init__(self, window, x, y):
		PatchElement.__init__(self, window, x, y)
		self.text = ''
		self.editable = False
		self.actor = clutter.Text()
		self.label = self.actor 

		# configure label
		self.actor.set_reactive(True)
		self.actor.set_color(window.color_unselected) 

		#self.actor.connect('text-changed', self.text_changed_cb)
		self.move(x, y)
		
		# add to stage 
		self.stage.register(self) 

	def unselect(self, *args):
		self.actor.set_editable(False)
		self.actor.set_color(self.stage.color_unselected) 
		self.text = self.actor.get_text()
		self.editable = False 

	def update_label(self, *args):
		self.message_text = self.actor.get_text()
		if self.obj_id is None:
			self.obj_id = MFPGUI().mfp.create("var")
		if self.obj_id is None:
			print "MessageElement: could not create message obj"
		else:
			self.send_params(message_text=self.message_text)

	def select(self, *args):
		self.actor.set_color(self.stage.color_selected) 


