#! /usr/bin/env python2.6
'''
message_element.py
A patch element corresponding to a clickable message

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter as clutter 
import cairo
import math 
from patch_element import PatchElement
from mfp import MFPGUI
from .modes.label_edit import LabelEditMode

class MessageElement (PatchElement):
	element_type = "message"

	def __init__(self, window, x, y):
		PatchElement.__init__(self, window, x, y)

		self.message_text = None 
		self.connections_out = [] 
		self.connections_in = [] 

		# create elements
		self.actor = clutter.Group()
		self.texture = clutter.CairoTexture()
		self.label = clutter.Text()

		self.texture.set_size(35, 25)

		self.actor.set_reactive(True)
		self.actor.add_actor(self.texture)
		self.actor.add_actor(self.label)

		# configure rectangle box 
		self.draw_border()

		# configure label
		self.label.set_position(4, 1)
		self.label.set_color(window.color_unselected) 
		self.label.connect('text-changed', self.text_changed_cb)

		# click handler 
		self.actor.connect('button-press-event', self.button_press_cb)
		
		self.move(x, y)

		# request update when value changes
		self.update_required = True

		# add components to stage 
		self.stage.register(self)

	def draw_border(self):
		w = self.texture.get_property('surface_width')-2
		h = self.texture.get_property('surface_height')-2
		print "draw_border: w=%s, h=%s" % (w, h)
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
		ct.curve_to(w-8, h-8, w-8, 8, w, 1)
		ct.line_to(1,1)
		ct.close_path()
		ct.stroke()

	def button_press_cb(self, *args):
		print "button press", args
		MFPGUI().mfp.send_bang(self.obj_id, 0) 

	def label_edit_start(self):
		pass

	def label_edit_finish(self, *args):
		self.message_text = self.label.get_text()

		print "MessageElement: obj=%s" % (self.message_text)
		self.create("message", self.message_text)
		if self.obj_id is None:
			print "MessageElement: could not create message obj"
		else:
			self.send_params()
			self.draw_ports()

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

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		self.actor.set_position(x, y)

		for c in self.connections_out:
			c.draw()
		
		for c in self.connections_in:
			c.draw()

	def configure(self, params):
		self.label.set_text(repr(params.get('value')))
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
		return LabelEditMode(self.stage, self, self.label)




