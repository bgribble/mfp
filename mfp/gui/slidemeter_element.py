#! /usr/bin/env python
'''
slidemeter_element.py
A patch element corresponding to a vertical or horizontal slider/meter

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter as clutter 
import math 
from patch_element import PatchElement
from .modes.slider import SliderEditMode, SliderControlMode
from mfp import MFPGUI
from mfp import log 
from . import ticks 

class SlideMeterElement (PatchElement):
	'''
	Vertical/horizontal slider/meter element
	Contains an optional scale and an optional title
	Can be output-only or interactive 
	Scale can be dB or linear
	'''

	element_type = "var"
	DEFAULT_W = 25 
	DEFAULT_H = 100
	TITLE_SPACE = 22
	SCALE_SPACE = 30 
	TICK_SPACE = 14
	TICK_LEN = 5

	def __init__(self, window, x, y):
		PatchElement.__init__(self, window, x, y)

		# parameters controlling display
		self.value = 0.0
		self.title = None 
		self.title_text = None 
		self.min_value = 0.0
		self.max_value = 1.0 
		self.scale_ticks = None
		self.scale_font_size = 8
		self.show_scale = False 
		self.show_title = True 
		self.slider_enable = True  

		# value to emit when at bottom of scale, useful for dB scales 
		self.slider_zero = None	

		# coordinates of "hot" (meter display) area, where 
		# dragging works 
		self.hot_x_min = None
		self.hot_x_max = None
		self.hot_y_min = None
		self.hot_y_max = None 

		# create elements
		self.texture = clutter.CairoTexture.new(self.DEFAULT_W, self.DEFAULT_H)
		self.title = clutter.Text()

		# configure 
		self.add_actor(self.texture)
		self.add_actor(self.title) 
		self.texture.connect("draw", self.draw_cb)
		
		self.set_reactive(True)

		self.set_size(self.DEFAULT_W, self.DEFAULT_H)
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
			v = (x - self.min_value) * bar_px / float(self.max_value-self.min_value)
			return v

		w = self.texture.get_property('surface_width')-2
		h = self.texture.get_property('surface_height')-2
		c = None
		if self.selected: 
			c = self.stage.color_selected
		else:
			c = self.stage.color_unselected
		ct.set_source_rgb(c.red, c.green, c.blue)
		
		scale_fraction = abs((self.value - self.min_value) / (self.max_value - self.min_value))
		self.hot_y_max = h
		self.hot_y_min = 1
		self.hot_x_min = 1 
		self.hot_x_max = w 

		if self.show_scale: 
			self.hot_x_min = self.SCALE_SPACE

		bar_h = self.hot_y_max-self.hot_y_min
		bar_w = self.hot_x_max-self.hot_x_min 

		# draw the scale if required
		if self.show_scale:
			ct.set_font_size(self.scale_font_size)
			
			if self.scale_ticks is None:
				num_ticks = bar_h/ self.TICK_SPACE 
				self.scale_ticks = ticks.linear(self.min_value, self.max_value, num_ticks)
				log.debug("ticks:", num_ticks, self.scale_ticks)
			for tick in self.scale_ticks:
				tickht = self.hot_y_max - pt2px(tick, bar_h)
				ct.move_to(self.hot_x_min-self.TICK_LEN, tickht)
				ct.line_to(self.hot_x_min, tickht)
				ct.stroke()
				ct.move_to(5, tickht)
				ct.show_text("%.3g" % tick)

		# draw the indicator and a surrounding box 
		ct.rectangle(self.hot_x_min, self.hot_y_min, bar_w, bar_h)
		ct.stroke()
		ct.rectangle(self.hot_x_min, bar_h*(1.0-scale_fraction), bar_w, bar_h*scale_fraction)
		ct.fill() 

	def point_in_slider(self, x, y): 
		orig_x, orig_y = self.get_position()
		x -= orig_x
		y -= orig_y
		if (self.hot_x_min <= x <= self.hot_x_max
			and self.hot_y_min <= y <= self.hot_y_max):
			return True 
		else:
			return False 

	def pixdelta2value(self, pixdelta):
		pix_h = self.texture.get_property('surface_height')-2
		#if self.show_title:
		#	pix_h -= self.TITLE_SPACE 
		return (float(pixdelta)/pix_h) * (self.max_value-self.min_value)

	def update_value(self, value):
		if value >= self.max_value:
			value = self.max_value 

		if value <= self.min_value:
			value = self.min_value 

		if value != self.value:
			self.value = value
			self.texture.clear()
			self.texture.invalidate()
			MFPGUI().mfp.send(self.obj_id, 0, self.value)

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		self.set_position(x, y)

		for c in self.connections_out:
			c.draw()
		
		for c in self.connections_in:
			c.draw()

	def configure(self, params):
		changes = False 
		
		v = params.get("show_scale")
		if v and not self.show_scale:
			self.show_scale = True 
			self.set_size(self.get_width() + self.SCALE_SPACE, self.get_height())
			if self.title: 
				self.recenter_title()
			changes = True
		elif v is False and self.show_scale:
			self.show_scale = False 
			self.set_size(self.get_width() - self.SCALE_SPACE, self.get_height())
			if self.title: 
				self.recenter_title()
			changes = True
		
		v = params.get("show_title")
		if v and not self.show_title:
			self.show_title = True 
			self.add_actor(self.title)
			self.set_size(self.get_width(), self.get_height() + self.TITLE_SPACE)
			changes = True
		elif v is False and self.show_title:
			self.show_title = False 
			self.remove_actor(self.title)
			self.set_size(self.get_width(), self.get_height() - self.TITLE_SPACE)
			changes = True
		
		for p in ("value", "slider_enable", "min_value", "max_value"):
			v = params.get(p)
			if v is not None and hasattr(self, p):
				changes = True 
				setattr(self, p, v)
				if p in ("min_value", "max_value"):
					self.scale_ticks = None 

		PatchElement.configure(self, params)
		if changes: 
			self.texture.clear()
			self.texture.invalidate()

	def set_size(self, width, height):
		self.width = width
		self.height = height 
		clutter.Group.set_size(self, self.width, self.height)
		if self.show_title:
			height -= self.TITLE_SPACE
			title_x, title_y = self.title.get_position()
			self.title.set_position(title_x, height-2)
		self.texture.set_size(width, height)
		self.texture.set_surface_size(width, height)

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

	def recenter_title(self):
		w = self.title.get_width()
		x,y = self.title.get_position()
		self.title.set_position((self.texture.get_width()-self.title.get_width())/2.0, y)

	def label_edit_start(self):
		pass

	def label_edit_finish(self, *args):
		self.title_text = self.title.get_text()
		if self.show_title and not self.title_text: 
			self.show_title = False 
			self.title_text = None 
			self.remove_actor(self.title)
			self.set_size(self.width, self.height)
			self.texture.invalidate()
		else:
			self.recenter_title()

	def make_edit_mode(self):
		return SliderEditMode(self.stage, self, self.title_text or "Fader/meter edit")

	def make_control_mode(self):
		return SliderControlMode(self.stage, self, self.title_text or "Fader/meter control")

class FaderElement(SlideMeterElement):
	pass

class BarMeterElement(SlideMeterElement):
	def __init__(self, window, x, y):
		SlideMeterElement.__init__(self, window, x, y)

		self.slider_enable = False 


	
