#! /usr/bin/env python2.6
'''
enum_element.py
A patch element corresponding to a number box or enum selector

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter
import math 
from patch_element import PatchElement
from mfp import MFPGUI
from .modes.label_edit import LabelEditMode
from .modes.enum_control import EnumControlMode

class EnumElement (PatchElement):
	element_type = "enum"
	PORT_TWEAK = 7 

	def __init__(self, window, x, y):
		PatchElement.__init__(self, window, x, y)

		self.value = 0
		self.digits = 1
		self.scientific = False 
		self.format_str = "%.1f"
		self.connections_out = [] 
		self.connections_in = [] 
		self.editable = False 
		self.update_required = True

		# create elements
		self.texture = Clutter.CairoTexture.new(35, 25)
		self.texture.connect("draw", self.draw_cb)
		self.label = Clutter.Text()

		self.set_reactive(True)
		self.add_actor(self.texture)
		self.add_actor(self.label)

		# configure label
		self.label.set_position(4, 1)
		self.label.set_color(window.color_unselected) 
		self.label.connect('text-changed', self.text_changed_cb)
		self.label.set_text(self.format_value(self.value))

		# click handler 
		# self.actor.connect('button-press-event', self.button_press_cb)
		
		self.move(x, y)
		self.texture.invalidate()

	def format_update(self):
		if self.scientific:
			oper = "e"
		else:
			oper = "f"
		self.format_str = "%%.%d%s" % (self.digits, oper)

	def format_value(self, value):
		return self.format_str % value 

	def draw_cb(self, texture, ct):
		w = self.texture.get_property('surface_width')-2
		h = self.texture.get_property('surface_height')-2
		self.texture.clear()
		if self.selected: 
			color = self.stage.color_selected
		else:
			color = self.stage.color_unselected

		ct.set_source_rgba(color.red, color.green, color.blue, 1.0)
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
			self.create(self.element_type, str(self.value))
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
		self.label.set_text(self.format_value(self.value))
		if self.obj_id is None:
			self.create_obj()
		MFPGUI().mfp.send(self.obj_id, 0, self.value)

	def label_edit_start(self):
		pass

	def label_edit_finish(self, *args):
		# called by labeleditmode
		t = self.label.get_text()
		self.update_value(float(t))
		if self.obj_id is None:
			self.create_obj()
		MFPGUI().mfp.send(self.obj_id, 0, self.value)

	def configure(self, params):
		fmt_changed = False 
		val_changed = False 

		v = params.get("value", float(self.obj_args or 0.0))
		if v != self.value: 
			self.value = v
			val_changed = True 

		v = params.get("scientific")
		if v:
			if not self.scientific: 
				fmt_changed = True 
			self.scientific = True 
		else: 
			if self.scientific: 
				fmt_changed = True 
			self.scientific = False 

		v = params.get("digits") 
		if v is not None and v != self.digits: 
			self.digits = v
			fmt_changed = True 

		if fmt_changed: 
			self.format_update()
		if fmt_changed or val_changed: 
			self.label.set_text(self.format_value(self.value))
		PatchElement.configure(self, params)	

	def port_position(self, port_dir, port_num):
		# tweak the right input port display to be left of the slant 
		if port_dir == PatchElement.PORT_IN and port_num == 1:
			default = PatchElement.port_position(self, port_dir, port_num)
			return (default[0] - self.PORT_TWEAK, default[1])
		else:
			return PatchElement.port_position(self, port_dir, port_num)

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
		return LabelEditMode(self.stage, self, self.label)

	def make_control_mode(self):
		return EnumControlMode(self.stage, self)

