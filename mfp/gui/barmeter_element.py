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
from mfp import log 

class BarMeterElement (PatchElement):
	'''
	Vertical/horizontal bar meter element
	Contains an optional scale and an optional title
	Scale can be dB or linear
	'''

	element_type = "var"
	DEFAULT_W = 40
	DEFAULT_H = 100
	VERT = 0 
	HORIZ = 1 
	LIN_SCALE = 0
	DB_SCALE = 1

	def __init__(self, window, x, y):
		PatchElement.__init__(self, window, x, y)

		# parameters controlling display
		self.value = 0.0
		self.title = None 
		self.orientation = self.VERT
		self.scale = self.LIN_SCALE 
		self.min_value = 0.0
		self.max_value = 1.0 
		self.show_scale = True
		self.show_title = True 

		# create elements
		self.texture = clutter.CairoTexture.new(self.DEFAULT_W, self.DEFAULT_H)

		# configure 
		self.texture.connect("draw", self.draw_cb)
		self.set_reactive(True)
		self.add_actor(self.texture)

		self.texture.invalidate()
		self.move(x, y)

		# request update when value changes
		self.update_required = True

		# create the underlying var
		self.create(self.element_type, str(self.value))
		if self.obj_id is None:
			print "PlotElement: could not create", self.obj_type, self.obj_args
		else:
			self.send_params()
			self.draw_ports()


	def draw_cb(self, texture, ct):
		w = self.texture.get_property('surface_width')-2
		h = self.texture.get_property('surface_height')-2
		c = None
		if self.selected: 
			c = self.stage.color_selected
		else:
			c = self.stage.color_unselected
		ct.set_source_rgb(c.red, c.green, c.blue)
		
		scale_fraction = abs((self.value - self.min_value) / (self.max_value - self.min_value))
		ct.rectangle(1, 1, w, h)
		ct.stroke()
		ct.rectangle(2, h*(1.0-scale_fraction), w-1, h*scale_fraction)
		ct.fill() 

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
		v = params.get('value')
		if v is not None:
			self.value = v
			self.texture.clear()
			self.texture.invalidate()

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





