#! /usr/bin/env python2.6
'''
processor_element.py
A patch element corresponding to a signal or control processor 
'''

import clutter 
import math 
from patch_element import PatchElement
from mfp import MFPGUI
from input_mode import InputMode
from .modes.label_edit import LabelEditMode

class ProcessorElement (PatchElement):
	element_type = "processor"

	def __init__(self, window, x, y, params={}):
		PatchElement.__init__(self, window, x, y)
	
		self.connections_out = [] 
		self.connections_in = [] 

		# create elements 
		self.actor = clutter.Group()
		self.rect = clutter.Rectangle()
		self.label = clutter.Text()

		# configure rectangle box 
		self.rect.set_size(35, 20)
		self.rect.set_border_width(2)
		self.rect.set_border_color(window.color_unselected)
		self.rect.set_reactive(False)

		# configure label
		self.label.set_position(4, 1)
		self.label.set_color(window.color_unselected) 
		self.label.connect('text-changed', self.text_changed_cb)
		self.label.set_reactive(False)

		self.actor.add(self.rect)
		self.actor.add(self.label)
		self.actor.set_reactive(True)

		self.move(x, y)

		# add components to stage 
		self.stage.register(self)

	def update_label(self, *args):
		print "processor update label", args
		t = self.label.get_text()
		parts = t.split(' ', 1)
		self.obj_type = parts[0]
		if len(parts) > 1:
			self.obj_args = parts[1]

		print "ProcessorElement: processor=%s, args=%s" % (self.obj_type, self.obj_args)
		print self.label.get_text()
		self.obj_id = MFPGUI().mfp.create(self.obj_type, self.obj_args)
		if self.obj_id is None:
			print "ProcessorElement: could not create", self.obj_type, self.obj_args
		self.send_params()

	def text_changed_cb(self, *args):
		'''called by clutter when label.set_text or editing occurs'''

		lwidth = self.label.get_property('width') 
		bwidth = self.rect.get_property('width')
			
		new_w = None 
		if (lwidth > (bwidth - 14)):
			new_w = lwidth + 14
		elif (bwidth > 35) and (lwidth < (bwidth - 14)):
			new_w = max(35, lwidth + 14)

		if new_w is not None:
			self.rect.set_size(new_w, self.rect.get_property('height'))

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		self.actor.set_position(x, y)

		for c in self.connections_out:
			c.draw()
		
		for c in self.connections_in:
			c.draw()

	def select(self):
		self.selected = True 
		self.rect.set_border_color(self.stage.color_selected)

	def unselect(self):
		self.selected = False 
		self.rect.set_border_color(self.stage.color_unselected)

	def delete(self):
		print "processor delete:", self
		for c in self.connections_out+self.connections_in:
			c.delete()

		PatchElement.delete(self)

	def make_edit_mode(self):
		return LabelEditMode(self.stage, self, self.label)

	def configure(self, params):
		if self.obj_args is None:
			self.label.set_text("%s" % (self.obj_type,))
		else:
			self.label.set_text("%s %s" % (self.obj_type, self.obj_args))
		PatchElement.configure(self, params)	

