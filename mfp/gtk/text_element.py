#! /usr/bin/env python2.6
'''
text_element.py
A text element (comment) in a patch
'''

from gi.repository import Clutter as clutter 
from patch_element import PatchElement 
from mfp import MFPGUI
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

		#self.label.connect('text-changed', self.text_changed_cb)
		self.move(x, y)

	def unselect(self, *args):
		self.label.set_color(self.stage.color_unselected) 
		self.text = self.label.get_text()

	def label_edit_start(self):
		pass

	def label_edit_finish(self, *args):
		self.message_text = self.label.get_text()
		if self.obj_id is None:
			self.create("var", self.message_text)
		if self.obj_id is None:
			print "MessageElement: could not create message obj"
		else:
			self.send_params(message_text=self.message_text)
			self.draw_ports()

	def select(self, *args):
		self.label.set_color(self.stage.color_selected) 
	
	def make_edit_mode(self):
		return LabelEditMode(self.stage, self, self.label, multiline=True, markup=True)

	def configure(self, params):
		self.text = params.get('message_text')
		self.label.set_text(self.text)
		PatchElement.configure(self, params)	


