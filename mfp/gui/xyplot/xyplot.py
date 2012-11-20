#! /usr/bin/env python
'''
xyplot.py 
Clutter widget supporting scatter, line, and roll plots

Copyright (c) 2012 Bill Gribble <grib@billgribble.com> 
'''

from gi.repository import Clutter
import math

from .mark_style import MarkStyle
from .quilt import Quilt 
from .. import ticks 
from mfp import log 

black = Clutter.Color()
black.from_string("Black")

white = Clutter.Color()
white.from_string("White")

class XYPlot (Clutter.Group):
	MARGIN_LEFT = 30 
	MARGIN_BOT = 30
	AXIS_PAD = 5
	TICK_SIZE = 50

	SCATTER = 0
	CURVE = 1

	def __init__(self, width, height):
		Clutter.Group.__init__(self)

		self.width = width
		self.height = height

		self.style = {}

		# scaling params
		self.x_min = 0
		self.x_max = 6.28 
		self.y_min = -1
		self.y_max = 1
		self.axis_font_size = 8

		# initialized by create() call
		self.border = None
		self.plot_border = None
		self.x_axis = None
		self.y_axis = None
		self.plot = None
		self.plot_w = 0
		self.plot_h = 0

		self.create()

	def create(self):
		self.border = Clutter.Rectangle()
		self.border.set_border_width(0)
		self.border.set_border_color(black)
		self.border.set_color(white)
		self.border.set_size(self.width, self.height)
		self.border.set_position(0,0)
		self.add_actor(self.border)
		
		self.plot_w = self.width - self.MARGIN_LEFT
		self.plot_h = self.height - self.MARGIN_BOT

		self.x_axis = Quilt(self.plot_w, self.MARGIN_BOT)
		self.x_axis.set_position(self.MARGIN_LEFT, self.height-self.MARGIN_BOT)
		self.x_axis.set_viewport_origin(0, 0)
		self.add_actor(self.x_axis)

		self.y_axis = Quilt(self.MARGIN_LEFT, self.plot_h)
		self.y_axis.set_position(0, 0)
		self.y_axis.set_viewport_origin(0, -self.plot_h/2.0)
		self.add_actor(self.y_axis)

		self.x_axis.set_render_cb(self.draw_xaxis_cb)
		self.y_axis.set_render_cb(self.draw_yaxis_cb)

		self.plot_border = Clutter.Rectangle()
		self.plot_border.set_border_width(0)
		self.plot_border.set_border_color(black)
		self.plot_border.set_color(white)
		self.plot_border.set_size(self.plot_w, self.plot_h)
		self.plot_border.set_position(self.MARGIN_LEFT, 0)
		self.add_actor(self.plot_border)

		self.plot = Quilt(self.plot_w, self.plot_h)
		self.plot.set_position(self.MARGIN_LEFT, 0)
		self.plot.set_render_cb(self.draw_field_cb)
		self.plot.set_viewport_origin(0, -self.plot_h/2.0)
		self.add_actor(self.plot)
		
	def set_size(self, width, height):
		self.width = width
		self.height = height

		self.border.set_size(self.width, self.height)
		self.plot_w = self.width - self.MARGIN_LEFT
		self.plot_h = self.height - self.MARGIN_BOT
		self.x_axis.set_size(self.plot_w, self.MARGIN_BOT)
		self.x_axis.set_position(self.MARGIN_LEFT, self.height-self.MARGIN_BOT)
		self.y_axis.set_size(self.MARGIN_LEFT, self.plot_h)
		self.plot_border.set_size(self.plot_w, self.plot_h)
		self.plot.set_size(self.plot_w, self.plot_h)

		self.x_axis.redraw()
		self.y_axis.redraw()
		self.plot.redraw()

	def set_bounds(self, x_min, y_min, x_max, y_max):

		if ((x_min is None or x_min == self.x_min) 
	         and (x_max is None or x_max == self.x_max) 
			 and (y_min is None or y_min == self.y_min) 
	         and (y_max is None or y_max == self.y_max)):
			return

		if x_min is None:
			if x_max is not None:
				x_min = self.x_min + (x_max - self.x_max)
			else: 
				x_min = self.x_min
				x_max = self.x_max
		elif x_max is None:
			x_max = self.x_max + (x_min - self.x_min)

		if y_min is None:
			if y_max is not None:
				y_min = self.y_min + (y_max - self.y_max)
			else: 
				y_min = self.y_min
				y_max = self.y_max
		elif y_max is None:
			y_max = self.y_max + (y_min - self.y_min)

		# if scale is changing, really need to redraw all
		need_x_flush = need_y_flush = False 

		if (x_max - x_min != self.x_max-self.x_min):
			need_x_flush = True 

		if (y_max - y_min != self.y_max-self.y_min):
			need_y_flush = True

		if ((x_min != self.x_min) or (x_max != self.x_max)):
			self.x_min = x_min
			self.x_max = x_max
			origin = self.pt2px((x_min, 0))
			self.x_axis.set_viewport_origin(origin[0], origin[1], need_x_flush)

		if ((y_min != self.y_min) or (y_max != self.y_max)):
			self.y_min = y_min
			self.y_max = y_max
			origin = self.pt2px((0, y_max))
			self.y_axis.set_viewport_origin(origin[0], origin[1], need_y_flush)

		origin = self.pt2px((x_min, y_max))
		if need_x_flush or need_y_flush:
			self.reindex()

		self.plot.set_viewport_origin(origin[0], origin[1], need_x_flush or need_y_flush)

	def pt2screen(self, p):
		np = [(p[0] - self.x_min)*float(self.plot_w)/(self.x_max - self.x_min),
		      self.plot_h - (p[1] - self.y_min)*float(self.plot_h)/(self.y_max - self.y_min)]
		return np

	def pt2px(self, p):
		np = [p[0]*float(self.plot_w)/(self.x_max - self.x_min),
		      -1.0*p[1]*float(self.plot_h)/(self.y_max - self.y_min)]
		return np

	def px2pt(self, p):
		np = [p[0]/(float(self.plot_w)/(self.x_max - self.x_min)),
		      -1.0*p[1]/(float(self.plot_h)/(self.y_max - self.y_min))]
		return np

	def draw_xaxis_cb(self, texture, ctx, px_min, px_max):
		pt_min = self.px2pt(px_min)
		pt_max = self.px2pt(px_max)

		tick_pad = self.px2pt((self.TICK_SIZE, 0))[0]
		tick_min = pt_min[0] - 2*tick_pad 
		tick_max = pt_max[0] + tick_pad  

		# X axis
		xticks = ticks.linear(self.x_min, self.x_max, self.plot_w/self.TICK_SIZE,
								   tick_min, tick_max)
		ctx.set_source_rgb(black.red, black.green, black.blue)
		ctx.set_font_size(self.axis_font_size)

		# the axis line
		ctx.move_to(0, self.AXIS_PAD)
		ctx.line_to(texture.get_width(), self.AXIS_PAD)
		ctx.stroke()

		# ticks
		for tick in xticks:
			tick_px = self.pt2px((tick, 0))
			ctx.move_to(tick_px[0]-px_min[0], self.AXIS_PAD)
			ctx.line_to(tick_px[0]-px_min[0], 3*self.AXIS_PAD)
			ctx.stroke()
			ctx.move_to(tick_px[0]-px_min[0], self.MARGIN_BOT-self.AXIS_PAD)
			ctx.show_text("%.3g" % tick)

	def draw_yaxis_cb(self, texture, ctx, px_min, px_max):
		pt_min = self.px2pt(px_min)
		pt_max = self.px2pt(px_max)

		tick_pad = abs(self.px2pt((0, self.TICK_SIZE))[1])
		tick_min = pt_max[1] - 2*tick_pad 
		tick_max = pt_min[1] + tick_pad  

		# Y axis ticks
		yticks = ticks.linear(self.y_min, self.y_max, float(self.plot_h)/self.TICK_SIZE, 
							   tick_min, tick_max)
		ctx.set_source_rgb(black.red, black.green, black.blue)
		ctx.set_font_size(self.axis_font_size)
		
		# the axis line
		ctx.move_to(self.MARGIN_LEFT - self.AXIS_PAD, 0)
		ctx.line_to(self.MARGIN_LEFT - self.AXIS_PAD, texture.get_height())
		ctx.stroke()

		# ticks
		for tick in yticks:
			tick_px = self.pt2px((0,tick))
			ctx.move_to(self.MARGIN_LEFT-self.AXIS_PAD, tick_px[1]-px_min[1])
			ctx.line_to(self.MARGIN_LEFT-3*self.AXIS_PAD, tick_px[1]-px_min[1])
			ctx.stroke()
			ctx.save()
			ctx.move_to(self.AXIS_PAD, tick_px[1]-px_min[1])
			ctx.rotate(math.pi/2)
			ctx.show_text("%.3g" % tick)
			ctx.restore()
