#! /usr/bin/env python2.6
'''
barmeter_element.py
A patch element corresponding to a vertical or horizontal bar gauge or slider 

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter as clutter 
import cairo
import math 
from patch_element import PatchElement
from .modes.label_edit import LabelEditMode
from mfp import MFPGUI
from mfp import log 
from . import ticks 

class BarMeterElement (PatchElement):
	'''
	Vertical/horizontal bar meter/slider element
	Contains an optional scale and an optional title
	Can be output-only or interactive 
	Scale can be dB or linear
	'''

	element_type = "var"
	DEFAULT_W = 60
	DEFAULT_H = 120
	VERT = 0 
	HORIZ = 1 
	TITLE_SPACE = 25
	TICK_SPACE = 14
	TICK_LEN = 5

	def __init__(self, window, x, y):
		PatchElement.__init__(self, window, x, y)

		# parameters controlling display
		self.value = 0.0
		self.title = None 
		self.orientation = self.VERT

		self.min_value = 0.0
		self.max_value = 1.0 
		self.scale_ticks = None
		self.scale_font_size = 8
		self.show_scale = True
		self.show_title = True 

		self.slider_enable = False 
		self.slider_zero = True 

		# create elements
		self.texture = clutter.CairoTexture.new(self.DEFAULT_W, self.DEFAULT_H)
		self.title = clutter.Text()

		# configure 
		self.add_actor(self.texture)
		self.add_actor(self.title) 
		self.texture.connect("draw", self.draw_cb)
		self.title.set_position(4, self.DEFAULT_H-self.TITLE_SPACE)
		
		self.set_reactive(True)

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
		def pt2px(x, bar_px):
			return x * bar_px / (self.max_value-self.min_value)

		w = self.texture.get_property('surface_width')-2
		h = self.texture.get_property('surface_height')-2
		c = None
		if self.selected: 
			c = self.stage.color_selected
		else:
			c = self.stage.color_unselected
		ct.set_source_rgb(c.red, c.green, c.blue)
		
		scale_fraction = abs((self.value - self.min_value) / (self.max_value - self.min_value))
		bar_bottom = h
		bar_top = 1
		bar_left = 1 
		bar_right = w 

		if self.show_scale: 
			bar_left = w/2.0
		if self.show_title: 
			bar_bottom = h - self.TITLE_SPACE

		bar_h = bar_bottom-bar_top
		bar_w = bar_right-bar_left 

		# draw the scale if required
		if self.show_scale:
			ct.set_font_size(self.scale_font_size)
			
			if self.scale_ticks is None:
				num_ticks = bar_h/ self.TICK_SPACE 
				self.scale_ticks = ticks.linear(self.min_value, self.max_value, num_ticks)
			for tick in self.scale_ticks:
				tickht = bar_bottom - pt2px(tick, bar_h)
				ct.move_to(bar_left-self.TICK_LEN, tickht)
				ct.line_to(bar_left, tickht)
				ct.stroke()
				ct.move_to(5, tickht)
				ct.show_text("%.3g" % tick)

		# draw the title if required 
		if self.show_title:
			pass
		# draw the indicator and a surrounding box 
		ct.rectangle(bar_left, bar_top, bar_w, bar_h)
		ct.stroke()
		ct.rectangle(bar_left, bar_h*(1.0-scale_fraction), bar_w, bar_h*scale_fraction)
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

	def label_edit_start(self):
		pass

	def label_edit_finish(self, *args):
		self.title_text = self.title.get_text()
		log.debug("barmeter: label_edit_finish, '%s'" % self.title_text)
		if not self.title_text: 
			log.debug("barmeter: no title text, deleting object")
			self.show_title = False 
			self.title_text = None 
			self.remove_actor(self.title)
			del self.title
			self.title = None 
		w = self.title.get_width()
		x,y = self.title.get_position()
		self.title.set_position((self.texture.get_width()-self.title.get_width())/2.0, y)
		self.texture.invalidate()

	def make_edit_mode(self):
		return LabelEditMode(self.stage, self, self.title)




