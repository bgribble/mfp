#! /usr/bin/env python2.6
'''
via_element.py
A patch element corresponding to a send or receive box 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter
import math 
from patch_element import PatchElement
from mfp import MFPGUI
from .modes.label_edit import LabelEditMode
from .modes.enum_control import EnumControlMode

class ViaElement (PatchElement):
	display_type = "via"
	proc_type = "send"

	VIA_SIZE = 10
	VIA_FUDGE = 5 
	LABEL_FUDGE = 2 
	def __init__(self, window, x, y):
		PatchElement.__init__(self, window, x, y)

		self.connections_out = [] 
		self.connections_in = [] 
		self.editable = False 

		# create elements
		self.texture = Clutter.CairoTexture.new(self.VIA_SIZE+self.VIA_FUDGE, 
												self.VIA_SIZE+self.VIA_FUDGE)
		self.texture.connect("draw", self.draw_cb)
		self.label = Clutter.Text()
		self.label.set_position(4, self.VIA_SIZE+self.VIA_FUDGE+self.LABEL_FUDGE)
		self.set_reactive(True)
		self.add_actor(self.texture)
		self.add_actor(self.label)

		# configure label
		self.label.set_color(window.color_unselected) 
		self.label.connect('text-changed', self.text_changed_cb)

		# click handler 
		# self.actor.connect('button-press-event', self.button_press_cb)
		self.move(x, y)
		self.texture.invalidate()

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
		ct.set_line_width(3)
		cent = (self.VIA_SIZE + self.VIA_FUDGE)/2.0
		ct.arc(cent, cent, self.VIA_SIZE/2.0, 0, 2*math.pi)
		ct.stroke()

	def recenter_label(self):
		w = self.label.get_width()
		x,y = self.label.get_position()
		self.label.set_position((self.texture.get_width()-self.label.get_width())/2.0, y)

	def text_changed_cb(self, *args):
		self.recenter_label()

	def create_obj(self, label_text):
		if self.obj_id is None:
			self.create(self.proc_type, '"%s"' %label_text)
		if self.obj_id is None:
			print "ViaElement: could not create via obj"

		self.send_params()

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		self.set_position(x, y)

		for c in self.connections_out:
			c.draw()
		
		for c in self.connections_in:
			c.draw()

	def label_edit_start(self):
		pass

	def label_edit_finish(self, *args):
		# called by labeleditmode
		t = self.label.get_text()
		if self.obj_id is None:
			self.create_obj(t)
		self.recenter_label()

	def configure(self, params):
		PatchElement.configure(self, params)	

	def port_position(self, port_dir, port_num):
		# tweak the right input port display to be left of the slant 
		return (self.VIA_SIZE/2.0, self.VIA_SIZE/2.0)

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

