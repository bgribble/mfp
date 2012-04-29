#! /usr/bin/env python
'''
xyplot.py 
clutter widget supporting scatter, line, and roll plots

Copyright (c) 2012 Bill Gribble <grib@billgribble.com> 
'''

import clutter
import math

black = clutter.color_from_string("Black")
white = clutter.color_from_string("White")

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

class XYPlot (object):

	MARGIN_LEFT = 25
	MARGIN_BOT = 25
	AXIS_PAD = 5
	TICK_SIZE = 50

	SCATTER = 0
	CURVE = 1

	def __init__(self, stage, width, height, title):
		self.stage = stage
		self.width = width
		self.height = height
		self.title = title
		self.points = []
		self.mode = XYPlot.SCATTER

		# state
		self.drawn = {}

		# scaling params
		self.x_min = 0
		self.x_max = 6.28 
		self.y_min = -1
		self.y_max = 1

		# initialized by create() call
		self.cl_bg = None
		self.cl_title = None
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
		self.cl_bg.set_border_width(2)
		self.cl_bg.set_border_color(black)
		self.cl_bg.set_color(white)
		self.cl_bg.set_size(self.width, self.height)
		self.cl_group.add(self.cl_bg)
		
		self.cl_title = clutter.Text()
		self.cl_title.set_text(self.title)
		self.cl_title.set_position(0, 0)
		self.cl_group.add(self.cl_title)

		self.cl_field_w = self.width - 3*self.MARGIN_LEFT
		self.cl_field_h = self.height - 3*self.MARGIN_BOT

		self.cl_xaxis_bg = clutter.CairoTexture(self.cl_field_w, 2*self.MARGIN_BOT)
		self.cl_xaxis_bg.set_position(2*self.MARGIN_LEFT, self.height-2*self.MARGIN_BOT)
		self.cl_group.add(self.cl_xaxis_bg)

		self.cl_yaxis_bg = clutter.CairoTexture(2*self.MARGIN_LEFT, self.cl_field_h)
		self.cl_yaxis_bg.set_position(0, self.MARGIN_BOT)
		self.cl_group.add(self.cl_yaxis_bg)

		self.cl_field = clutter.Rectangle()
		self.cl_field.set_border_width(1)
		self.cl_field.set_border_color(black)
		self.cl_field.set_color(white)
		self.cl_field.set_size(self.cl_field_w, self.cl_field_h)
		self.cl_field.set_position(2*self.MARGIN_LEFT, self.MARGIN_BOT)
		self.cl_group.add(self.cl_field)

		self.cl_curve = clutter.CairoTexture(self.cl_field_w, self.cl_field_h)
		self.cl_curve.set_position(2*self.MARGIN_LEFT, self.MARGIN_BOT)
		self.cl_group.add(self.cl_curve)

		self.stage.add(self.cl_group)

	def pt_pos(self, p):
		np = [(p[0] - self.x_min)*float(self.cl_field_w)/(self.x_max - self.x_min),
		      self.cl_field_h - (p[1] - self.y_min)*float(self.cl_field_h)/(self.y_max - self.y_min)]
		return np

	def draw_axes(self):
		# X axis
		ticks = mkticks(self.x_min, self.x_max, self.cl_field_w/self.TICK_SIZE)
		self.cl_xaxis_bg.clear()
		ctx = self.cl_xaxis_bg.cairo_create()
		ctx.set_source_color(black)
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
			ctx.move_to(p[0], self.AXIS_PAD+self.MARGIN_BOT)
			ctx.show_text("%.3g" % tick)
		del ctx

		# Y axis
		ticks = mkticks(self.y_min, self.y_max, float(self.cl_field_h)/self.TICK_SIZE)
		self.cl_yaxis_bg.clear()
		ctx = self.cl_yaxis_bg.cairo_create()
		ctx.set_source_color(black)
		
		# the axis line
		ctx.move_to(2*self.MARGIN_LEFT-self.AXIS_PAD, 0)
		ctx.line_to(2*self.MARGIN_LEFT-self.AXIS_PAD, self.cl_field_h)
		ctx.stroke()

		# ticks
		for tick in ticks:
			p = self.pt_pos([0, tick])
			ctx.move_to(2*self.MARGIN_LEFT-self.AXIS_PAD, p[1])
			ctx.line_to(2*self.MARGIN_LEFT-3*self.AXIS_PAD, p[1])
			ctx.stroke()
			ctx.save()
			ctx.move_to(self.AXIS_PAD, p[1])
			ctx.rotate(math.pi/2)
			ctx.show_text("%.3g" % tick)
			ctx.restore()

		del ctx

	def append(self, point):
		self.points.append(point)

	def clear():
		self.cl_curve.clear()
		self.drawn = {}

	def update(self):
		pts = [ p for p in self.points if not self.drawn.has_key(p) ]
		if self.mode == XYPlot.SCATTER:
			self.draw_scatter(pts)
		elif self.mode == XYPlot.CURVE:
			self.draw_curve(pts)

	def draw_scatter(self, points):
		if not len(points):
			return

		ctxt = self.cl_curve.cairo_create()
		ctxt.scale(1.0, 1.0)
		ctxt.set_source_color(black)

		for p in points:
			pc = self.pt_pos(p)
			ctxt.move_to(pc[0], pc[1])
			ctxt.arc(pc[0], pc[1], 1.0, 0, math.pi * 2)
			self.drawn[p] = True
		ctxt.stroke()
		del ctxt

	def draw_curve(self, points):
		if not len(points):
			return

		ctxt = self.cl_curve.cairo_create()
		ctxt.scale(1.0, 1.0)
		ctxt.set_source_color(black)

		p = self.pt_pos(points[0])
		ctxt.move_to(p[0], p[1])

		for p in points[1:]:
			pc = self.pt_pos(p)
			ctxt.line_to(pc[0], pc[1])
			self.drawn[p] = True
		del self.drawn[points[-1]]
		ctxt.stroke()
		del ctxt

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

