#! /usr/bin/env python
'''
xyplot.py 
clutter widget supporting scatter, line, and roll plots

Copyright (c) 2012 Bill Gribble <grib@billgribble.com> 
'''

from gi.repository import Clutter as clutter
import math

black = clutter.Color()
black.from_string("Black")

white = clutter.Color()
white.from_string("White")

def mkticks(vmin, vmax, numticks):
	interv = float(vmax-vmin)/numticks
	logbase = pow(10, math.floor(math.log10(interv)))
	choices = [ logbase, logbase*2.5, logbase*5.0, logbase * 10]
	diffs = [ abs(interv-c) for c in choices ]
	tickint = choices[diffs.index(min(*diffs))]
	tickbase = tickint * math.floor(vmin / tickint)
	numticks = int(float(vmax-vmin) / tickint) + 2
	ticks = [ tickbase + n*tickint for n in range(numticks) ]
	return [ t for t in ticks if t >= vmin and t <= vmax ]

class MarkStyler (object):
	def __init__(self):
		self.col_r = 0
		self.col_g = 0
		self.col_b = 0
		self.shape = "dot"
		self.size = 1.0
		self.fill = True
		self.size_elt = None
		self.alpha_elt = None

	def set_color(self, r, g, b):
		self.col_r = r
		self.col_g = g
		self.col_b = b

	def set_shape(self, shape):
		self.shape = shape

	def mark_dot(self, ctx, point):
		ctx.move_to(point[0], point[1])
		ctx.arc(point[0], point[1], self.size, 0, math.pi * 2)

	def mark(self, ctx, point):
		if self.shape == "dot":
			self.mark_dot(ctx, point)


class XYPlot (object):

	MARGIN_LEFT = 30 
	MARGIN_BOT = 30
	AXIS_PAD = 5
	TICK_SIZE = 50

	SCATTER = 0
	CURVE = 1

	def __init__(self, stage, width, height):
		self.stage = stage
		self.width = width
		self.height = height

		self.mode = XYPlot.SCATTER
		self.points = {} 
		self.style = {}

		# scaling params
		self.x_min = 0
		self.x_max = 6.28 
		self.y_min = -1
		self.y_max = 1

		# initialized by create() call
		self.cl_bg = None
		self.cl_xaxis_bg = None
		self.cl_yaxis_bg = None
		self.cl_field = None
		self.cl_curve = None
		self.cl_field_w = 0
		self.cl_field_h = 0

		self.create()

	def create(self):
		self.cl_group = clutter.Group()

		self.cl_bg = clutter.Rectangle()
		self.cl_bg.set_border_width(0)
		self.cl_bg.set_border_color(black)
		self.cl_bg.set_color(white)
		self.cl_bg.set_size(self.width, self.height)
		self.cl_bg.set_position(0,0)
		self.cl_group.add_actor(self.cl_bg)
		
		self.cl_field_w = self.width - self.MARGIN_LEFT
		self.cl_field_h = self.height - self.MARGIN_BOT

		self.cl_xaxis_bg = clutter.CairoTexture.new(self.cl_field_w, self.MARGIN_BOT)
		self.cl_xaxis_bg.set_position(self.MARGIN_LEFT, self.height-self.MARGIN_BOT)
		self.cl_group.add_actor(self.cl_xaxis_bg)

		self.cl_yaxis_bg = clutter.CairoTexture.new(self.MARGIN_LEFT, self.cl_field_h)
		self.cl_yaxis_bg.set_position(0, 0)
		self.cl_group.add_actor(self.cl_yaxis_bg)

		self.cl_xaxis_bg.connect("draw", self.draw_xaxis_cb)
		self.cl_yaxis_bg.connect("draw", self.draw_yaxis_cb)

		self.cl_field = clutter.Rectangle()
		self.cl_field.set_border_width(0)
		self.cl_field.set_border_color(black)
		self.cl_field.set_color(white)
		self.cl_field.set_size(self.cl_field_w, self.cl_field_h)
		self.cl_field.set_position(self.MARGIN_LEFT, 0)

		self.cl_group.add_actor(self.cl_field)

		self.cl_curve = clutter.CairoTexture.new(self.cl_field_w, self.cl_field_h)
		self.cl_curve.set_position(self.MARGIN_LEFT, 0)
		self.cl_curve.connect("draw", self.draw_cb)
		self.cl_group.add_actor(self.cl_curve)

		self.stage.add_actor(self.cl_group)
		
		self.redraw_axes()

	def redraw_axes(self):
		self.cl_xaxis_bg.invalidate()
		self.cl_yaxis_bg.invalidate()

	def set_size(self, width, height):
		self.width = width
		self.height = height

		self.cl_bg.set_size(self.width, self.height)
		self.cl_field_w = self.width - self.MARGIN_LEFT
		self.cl_field_h = self.height - self.MARGIN_BOT
		self.cl_xaxis_bg.set_size(self.cl_field_w, self.MARGIN_BOT)
		self.cl_xaxis_bg.set_position(self.MARGIN_LEFT, self.height-self.MARGIN_BOT)
		self.cl_yaxis_bg.set_size(self.MARGIN_LEFT, self.cl_field_h)
		self.cl_field.set_size(self.cl_field_w, self.cl_field_h)
		self.cl_curve.set_size(self.cl_field_w, self.cl_field_h)
		self.redraw_axes()

	def set_position(self, x, y):
		self.cl_group.set_position(x, y)

	def pt_pos(self, p):
		np = [(p[0] - self.x_min)*float(self.cl_field_w)/(self.x_max - self.x_min),
		      self.cl_field_h - (p[1] - self.y_min)*float(self.cl_field_h)/(self.y_max - self.y_min)]
		return np

	def draw_xaxis_cb(self, texture, ctx):
		# X axis
		ticks = mkticks(self.x_min, self.x_max, self.cl_field_w/self.TICK_SIZE)
		ctx.set_source_rgb(black.red, black.green, black.blue)
		ctx.set_font_size(8)

		# the axis line
		ctx.move_to(0, self.AXIS_PAD)
		ctx.line_to(self.cl_field_w, self.AXIS_PAD)
		ctx.stroke()

		# ticks
		for tick in ticks:
			p = self.pt_pos([tick, 0])
			ctx.move_to(p[0], self.AXIS_PAD)
			ctx.line_to(p[0], 3*self.AXIS_PAD)
			ctx.stroke()
			ctx.move_to(p[0], self.MARGIN_BOT-self.AXIS_PAD)
			ctx.show_text("%.3g" % tick)

	def draw_yaxis_cb(self, texture, ctx):
		# Y axis
		ticks = mkticks(self.y_min, self.y_max, float(self.cl_field_h)/self.TICK_SIZE)
		ctx.set_source_rgb(black.red, black.green, black.blue)
		
		# the axis line
		ctx.move_to(self.MARGIN_LEFT-self.AXIS_PAD, 0)
		ctx.line_to(self.MARGIN_LEFT-self.AXIS_PAD, self.cl_field_h)
		ctx.stroke()

		# ticks
		for tick in ticks:
			p = self.pt_pos([0, tick])
			ctx.move_to(self.MARGIN_LEFT-self.AXIS_PAD, p[1])
			ctx.line_to(self.MARGIN_LEFT-3*self.AXIS_PAD, p[1])
			ctx.stroke()
			ctx.save()
			ctx.move_to(self.AXIS_PAD, p[1])
			ctx.rotate(math.pi/2)
			ctx.show_text("%.3g" % tick)
			ctx.restore()

	def append(self, point, curve=0):
		pre = self.points.setdefault(curve, [])
		pre.append(point)

	def clear(self, curve=None):
		print "XYPlot.clear", curve
		if curve is None:
			self.points = {}
		elif curve is not None and self.points.has_key(curve):
			del self.points[curve]
		self.cl_curve.clear()
		self.cl_curve.invalidate()


	def update(self):
		self.cl_curve.invalidate()

	def draw_cb(self, texture, ctx):
		if self.mode == XYPlot.SCATTER:
			self.draw_scatter_cb(texture, ctx)
		elif self.mode == XYPlot.CURVE:
			self.draw_curve_cb(texture, ctx)

	def draw_scatter_cb(self, texture, ctxt):
		if not len(self.points):
			return
		print "in scatter draw cb"
		print self.points
		for curve in self.points:
			styler = self.style.get(curve)
			if styler is None:
				styler = self.style[curve] = MarkStyler()
			for p in self.points[curve]:
				pc = self.pt_pos(p)
				styler.mark(ctxt, pc)
		ctxt.stroke()

	def draw_curve_cb(self, texture, ctxt):
		if not len(self.points):
			return

		ctxt.scale(1.0, 1.0)
		ctxt.set_source_rgb(black.red, black.green, black.blue)

		p = self.pt_pos(self.points[0])
		ctxt.move_to(p[0], p[1])

		for p in self.points[1:]:
			pc = self.pt_pos(p)
			ctxt.line_to(pc[0], pc[1])
		ctxt.stroke()

if __name__ == "__main__":
	import math
	import glib

	pts = [[x/100.0, math.sin(x/100.0)] for x in range(0, 6280) ]

	glib.threads_init()
	clutter.threads_init()
	clutter.init()

	stg = clutter.Stage()
	stg.set_size(320, 240)
	sco = ScopeActor(stg, 320, 240, "Scope test")
	stg.show()
	
	def movecurve():
		sco.x_min += 0.1
		sco.x_max += 0.1
		sco.draw_axes()
		sco.draw_curve(pts)
		return True

	glib.idle_add(movecurve)
	sco.draw_curve(pts)
	clutter.main()	

