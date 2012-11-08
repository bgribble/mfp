#! /usr/bin/env python2.6
'''
text_element.py
A text element (comment) in a patch
'''

from gi.repository import Clutter as clutter 
from patch_element import PatchElement 
from mfp import MFPGUI
from mfp import log 
from .modes.label_edit import LabelEditMode

class TextElement (PatchElement):
	element_type = "text"

	def __init__(self, window, x, y):
		PatchElement.__init__(self, window, x, y)
		self.text = ''
		self.label = clutter.Text()

		# configure label
		self.label.set_reactive(True)
		self.label.set_color(window.color_unselected) 
		self.add_actor(self.label)
		self.update_required = True 

		self.move(x, y)

	def unselect(self, *args):
		self.label.set_color(self.stage.color_unselected) 
		#self.text = self.label.get_text()

	def label_edit_start(self):
		return self.text 

	def label_edit_finish(self, widget, new_text):
		self.text = new_text
		if self.obj_id is None:
			self.create("var")
		if self.obj_id is None:
			log.debug("TextElement: could not create obj")
		else:
			MFPGUI().mfp.send(self.obj_id, self.text, 0)
			self.draw_ports()

	def select(self, *args):
		self.label.set_color(self.stage.color_selected) 
	
	def make_edit_mode(self):
		return LabelEditMode(self.stage, self, self.label, multiline=True, markup=True)

	def configure(self, params):
		log.debug(params)
		if params.get('value') is not None:
			new_text = params.get('value')
			if new_text != self.text:
				self.text = new_text 
				self.label.set_markup(self.text)
		PatchElement.configure(self, params)	


