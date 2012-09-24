#! /usr/bin/env python2.6
'''
enum_element.py
A patch element corresponding to a number box or enum selector

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter as clutter 
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
		self.texture = clutter.CairoTexture.new(35, 20)
		self.texture.connect("draw", self.draw_cb)
		self.label = clutter.Text()

		self.set_reactive(True)
		self.add_actor(self.texture)
		self.add_actor(self.label)

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
		self.texture.invalidate()

	def draw_cb(self, texture, ct):
		w = self.texture.get_property('surface_width')-2
		h = self.texture.get_property('surface_height')-2
		self.texture.clear()
		if self.selected: 
			color = self.stage.color_selected
		else:
			color = self.stage.color_unselected

		ct.set_source_rgba(color.r, color.g, color.b, color.a)
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
			self.set_size(new_w, self.texture.get_height())
			self.texture.set_size(new_w, self.texture.get_height())
			self.texture.set_surface_size(int(new_w), self.texture.get_property('surface_height'))
			self.texture.invalidate()

	def create_obj(self):
		if self.obj_id is None:
			self.create("var", str(self.value))
		if self.obj_id is None:
			print "MessageElement: could not create message obj"

		self.send_params()
		self.draw_ports()

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		self.set_position(x, y)

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

	def label_edit_start(self):
		pass

	def label_edit_finish(self, *args):
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
		self.texture.invalidate()

	def unselect(self):
		self.selected = False 
		self.texture.invalidate()

	def delete(self):
		for c in self.connections_out+self.connections_in:
			c.delete()
		PatchElement.delete(self)

	def make_edit_mode(self):
		return LabelEditMode(self.stage, self, self.label, value=True)

	def make_control_mode(self):
		return EnumControlMode(self.stage, self)

