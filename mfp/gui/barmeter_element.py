#! /usr/bin/env python2.6
'''
barmeter_element.py
A patch element corresponding to a vertical or horizontal bar gauge

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter as clutter 
import cairo
import math 
from patch_element import PatchElement
from mfp import MFPGUI

class BarMeterElement (PatchElement):
	element_type = "var"
	DEFAULT_W = 20
	DEFAULT_H = 100

	def __init__(self, window, x, y):
		PatchElement.__init__(self, window, x, y)

		self.connections_out = [] 
		self.connections_in = [] 

		# create elements
		self.texture = clutter.CairoTexture.new(DEFAULT_W, DEFAULT_H)
		self.label = clutter.Text()

		self.texture.set_size(35, 25)
		self.texture.connect("draw", self.draw_cb)

		self.set_reactive(True)
		self.add_actor(self.texture)
		self.add_actor(self.label)

		self.texture.invalidate()

		# configure label
		self.label.set_position(4, 1)
		self.label.set_color(window.color_unselected) 
		self.label.connect('text-changed', self.text_changed_cb)

		# click handler 
		self.connect('button-press-event', self.button_press_cb)
		
		self.move(x, y)

		# request update when value changes
		self.update_required = True

	def draw_cb(self, texture, ct):
		w = self.texture.get_property('surface_width')-2
		h = self.texture.get_property('surface_height')-2
		c = None
		if self.selected: 
			c = self.stage.color_selected
		else:
			c = self.stage.color_unselected
		ct.set_source_rgb(c.red, c.green, c.blue)

		ct.close_path()
		ct.stroke()

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		self.set_position(x, y)

		for c in self.connections_out:
			c.draw()
		
		for c in self.connections_in:
			c.draw()

	def configure(self, params):
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





