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


class Quilt (clutter.Group):
	def __init__(self, w, h):
		clutter.Group.__init__(self)

		self.width = w
		self.height = h
		self.rectangle = clutter.Rectangle()
		self.textures = [ clutter.CairoTexture.new(1.5*w, 1.5*h) for n in [0,1]]
		self.vport_x = 0 
		self.vport_y = 0 

		self.timescale = 0.03   # 0.1 px/ms = 100 px/
		self.scrolling_x = False

		self.rectangle.set_size(w, h)
		self.rectangle.set_border_width(1)
		self.rectangle.set_border_color(black)
		self.rectangle.set_position(0,0)
		self.rectangle.set_depth(-1)
		self.add_actor(self.rectangle)

		self.add_actor(self.textures[0])
		self.textures[0].set_position(-0.25 * w, 0.25*h)
		self.textures[0].connect("draw", self.draw_cb)
		self.textures[0].invalidate()
		
		self.add_actor(self.textures[1])
		self.textures[1].set_position(1.25 * w, 0.25*h)
		self.textures[1].connect("draw", self.draw_cb)
		self.textures[1].invalidate()

	def draw_cb(self, tex, ctx):
		ctx.set_source_rgb(0,0,0)
		if tex == self.textures[0]:
			ctx.move_to(self.width/2.0, self.height/2.0)
			ctx.show_text("0")
		elif tex == self.textures[1]:
			ctx.move_to(self.width/2.0, self.height/2.0)
			ctx.show_text("1")
		else:
			ctx.move_to(self.width/2.0, self.height/2.0)
			ctx.show_text("?")
	
	def tile_0_cb(self, *args):
		anim_time_1 = 3.0*self.width/self.timescale
		self.textures[0].set_position(1.25 * self.width, 0.25*self.height)
		a2 = self.textures[0].animatev(clutter.AnimationMode.LINEAR, anim_time_1, ["x"], [anim_x])
		print "tile_0_cb"
		
	def tile_1_cb(self, *args):
		anim_time_1 = 3.0*self.width/self.timescale
		self.textures[1].set_position(1.25 * self.width, 0.25*self.height)
		a2 = self.textures[1].animatev(clutter.AnimationMode.LINEAR, anim_time_1, ["x"], [anim_x])
		print "tile_1_cb"

	def start_scroll(self):
		self.scrolling_x = True

		anim_time_0 = 1.5*self.width/self.timescale
		anim_x = -1.75 * self.width
		a1 = self.textures[0].animatev(clutter.AnimationMode.LINEAR, anim_time_0, ["x"], [anim_x])
		a1.connect("completed", self.tile_0_cb)

		anim_time_1 = 3.0*self.width/self.timescale
		a2 = self.textures[1].animatev(clutter.AnimationMode.LINEAR, anim_time_1, ["x"], [anim_x])
		a2.connect("completed", self.tile_1_cb)


class MarkStyler (object):
	SQRT_3 = 3.0**0.5

	def __init__(self):
		self.col_r = 0
		self.col_g = 0
		self.col_b = 0
		self.col_a = 255
		self.shape = "dot"
		self.size = 1.0
		self.fill = True
		self.size_elt = None
		self.alpha_elt = None

	def set_color(self, newcolor):
		r = g = b = 0
		a = 255

		if isinstance(newcolor, str):
			c = clutter.Color()
			c.from_string(newcolor)
			r = c.red
			g = c.green
			b = c.blue
			a = c.alpha
		elif isinstance(newcolor, (list, tuple)) and len(newcolor) > 2:
			r = newcolor[0]
			g = newcolor[1]
			b = newcolor[2]
			if len(newcolor) > 3:
				a = newcolor[3]

		self.col_r = r
		self.col_g = g
		self.col_b = b
		self.col_a = a

	def mark_dot(self, ctx, point):
		#ctx.move_to(point[0], point[1])
		ctx.arc(point[0], point[1], self.size, 0.0, math.pi * 2.0)

	def mark_square(self, ctx, point):
		dx = self.size/2.0
		x0 = point[0] - dx
		y0 = point[1] - dx
		x1 = point[0] + dx
		y1 = point[1] + dx
		ctx.move_to(x0, y0)
		ctx.line_to(x0, y1)
		ctx.line_to(x1, y1)
		ctx.line_to(x1, y0)
		ctx.line_to(x0, y0)

	def mark_triangle(self, ctx, point):
		d1 = self.size / 2.0
		d2 = self.SQRT_3 * self.size / 2.0
		ctx.move_to(point[0], point[1] - self.size)
		ctx.line_to(point[0] - d2, point[1] + d1)
		ctx.line_to(point[0] + d2, point[1] + d1)
		ctx.line_to(point[0], point[1] - self.size)

	def mark(self, ctx, point):
		ctx.set_source_rgba(self.col_r, self.col_g, self.col_b, self.col_a)
		if self.shape == "dot":
			self.mark_dot(ctx, point)
		elif self.shape == "square":
			self.mark_square(ctx, point)
		elif self.shape == "triangle":
			self.mark_triangle(ctx, point)

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

	def set_style(self, style):
		for inlet, istyle in style.items():
			marker = self.style.setdefault(inlet, MarkStyler()) 
			for k, v in istyle.items():
				if k == "size":
					marker.size = float(v)
				elif k == "color":
					marker.set_color(v)
				elif k == "shape":
					print "Assigning shape", marker, v
					marker.shape = str(v)

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
	clutter.init([])

	stg = clutter.Stage()
	stg.set_size(320, 240)
	
	q = Quilt(300,220)
	q.show()
	stg.add_actor(q)
	stg.show()	

	q.start_scroll()

	clutter.main()	

