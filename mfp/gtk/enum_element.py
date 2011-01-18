#! /usr/bin/env python2.6
'''
enum_element.py
A patch element corresponding to a number box or enum selector

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import clutter 
import cairo
import math 
from patch_element import PatchElement
from mfp import MFPGUI
from .modes.label_edit import LabelEditMode
from .modes.enum_control import EnumControlMode

class EnumElement (PatchElement):
	element_type = "enum"
	def __init__(self, window, x, y):
		PatchElement.__init__(self, window, x, y)

		self.value = 0
		self.connections_out = [] 
		self.connections_in = [] 
		self.editable = False 
		self.update_required = True

		# create elements
		self.actor = clutter.Group()
		self.texture = clutter.CairoTexture(35, 20)
		self.label = clutter.Text()

		self.actor.set_reactive(True)
		self.actor.add(self.texture)
		self.actor.add(self.label)

		# configure rectangle box 
		self.draw_border()

		# configure label
		self.label.set_position(4, 1)
		self.label.set_color(window.color_unselected) 
		self.label.connect('text-changed', self.text_changed_cb)
		self.label.set_text(str(self.value))

		# click handler 
		# self.actor.connect('button-press-event', self.button_press_cb)
		
		self.move(x, y)

		# add components to stage 
		self.stage.register(self)

	def draw_border(self):
		w = self.texture.get_property('surface_width')-2
		h = self.texture.get_property('surface_height')-2
		self.texture.clear()
		ct = self.texture.cairo_create()
		if self.selected: 
			ct.set_source_color(self.stage.color_selected)
		else:
			ct.set_source_color(self.stage.color_unselected)
		ct.translate(0.5, 0.5)
		ct.move_to(1,1)
		ct.line_to(1, h)
		ct.line_to(w, h)
		ct.line_to(w, h/3.0)
		ct.line_to(w-h/3.0, 1)
		ct.line_to(1,1)
		ct.close_path()
		ct.stroke()

	def text_changed_cb(self, *args):
		lwidth = self.label.get_property('width') 
		bwidth = self.texture.get_property('surface_width')
	
		new_w = None 
		if (lwidth > (bwidth - 20)):
			new_w = lwidth + 20
		elif (bwidth > 35) and (lwidth < (bwidth - 20)):
			new_w = max(35, lwidth + 20)

		if new_w is not None:
			self.texture.set_size(new_w, self.texture.get_height())
			self.texture.set_surface_size(int(new_w), self.texture.get_property('surface_height'))
			self.draw_border()

	def create_obj(self):
		if self.obj_id is None:
			self.obj_id = MFPGUI().mfp.create("var", str(self.value))
		if self.obj_id is None:
			print "MessageElement: could not create message obj"

		self.send_params()

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		self.actor.set_position(x, y)

		for c in self.connections_out:
			c.draw()
		
		for c in self.connections_in:
			c.draw()

	def update_value(self, value):
		# called by enumcontrolmode 
		self.value = value
		self.label.set_text(str(self.value))
		if self.obj_id is None:
			self.create_obj()
		MFPGUI().mfp.send(self.obj_id, 0, self.value)

	def update_label(self, *args):
		# called by labeleditmode
		t = self.label.get_text()
		self.update_value(int(t))
		if self.obj_id is None:
			self.create_obj()
		MFPGUI().mfp.send(self.obj_id, 0, self.value)

	def configure(self, params):
		v = params.get("value", int(self.obj_args))
		self.value = v
		self.label.set_text(str(self.value))
		PatchElement.configure(self, params)	

	def select(self):
		self.selected = True 
		self.draw_border()

	def unselect(self):
		self.selected = False 
		self.draw_border()

	def delete(self):
		for c in self.connections_out+self.connections_in:
			c.delete()
		PatchElement.delete(self)

	def make_edit_mode(self):
		return LabelEditMode(self.stage, self, self.label, value=True)

	def make_control_mode(self):
		return EnumControlMode(self.stage, self)
