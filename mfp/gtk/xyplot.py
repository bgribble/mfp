#! /usr/bin/env python
'''
xyplot.py 
clutter widget supporting scatter, line, and roll plots

Copyright (c) 2012 Bill Gribble <grib@billgribble.com> 
'''

from gi.repository import Clutter as clutter
import gobject
import cairo
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
	IDLE_INTERVAL = 2000

	def __init__(self, width, height, tilesize=100):
		clutter.Group.__init__(self)
		self.set_clip(0, 0, width, height)

		self.viewport_width = width
		self.viewport_height = height

		self.viewport_x = 0
		self.viewport_y = 0
		self.viewport_vx = False
		self.viewport_vy = False

		self.tile_group = clutter.Group()
		self.tile_group.show()
		self.add_actor(self.tile_group)

		self.tile_animation = None
		self.tile_size = tilesize
		self.tile_by_pos = {}
		self.tile_reverse = {}

		self.render_cb = None

		self.rebuild_quilt()

	def set_viewport_scroll(self, vx, vy):
		'''
		start scrolling viewport in the specified dir (pixels/sec)
		note tile group moves in opposite direction, vp stationary
		'''
		print "starting scroll", vx, vy

		def idle(*args):
			print "=========== IDLE ============="
			pos = self.tile_group.get_position()
			self.viewport_x = -pos[0]
			self.viewport_y = -pos[1]
			self.rebuild_quilt()
			return True

		def complete(*args):
			print "animation complete"

		if (vx != self.viewport_vx) or (vy != self.viewport_vy):
			self.viewport_vx = vx
			self.viewport_vy = vy

			target_x, target_y = self.tile_group.get_position()
			print "ANIMATE starting at", target_x, target_y

			target_x -= vx
			target_y -= vy 

			self.tile_animation = self.tile_group.animatev(clutter.AnimationMode.LINEAR, 50000,
														  ['x', 'y'],
														  [ target_x, target_y ])
			self.tile_animation.connect("completed", complete)

			glib.timeout_add(1000, idle)

	def rebuild_quilt(self):
		def lbound(val):
			return int(math.floor(val / float(self.tile_size)) * self.tile_size)

		def ubound(val):
			return lbound(val) + self.tile_size

		min_x = lbound(self.viewport_x)
		max_x = ubound(self.viewport_x + self.viewport_width)

		min_y = lbound(self.viewport_y)
		max_y = ubound(self.viewport_y + self.viewport_height)
	
		needed = {}
		for x in range(min_x, max_x, self.tile_size):
			for y in range(min_y, max_y, self.tile_size):
				needed[(x, y)] = True

		# alloc_tiles will kick off the redraw process
		self.alloc_tiles(needed)

	def alloc_tiles(self, needed):
		print "alloc_tiles:", needed

		garbage = self.gc_tiles(needed)
		for pos in needed:
			tile = self.tile_by_pos.get(pos)
			if tile is None:
				if garbage:
					self.move_tile(garbage[0], pos)
					garbage = garbage[1:]
				else:
					self.new_tile(pos)
		
	def gc_tiles(self, marked):
		garbage = []
		for pos, tile in self.tile_by_pos.items():
			if marked.get(pos) is None:
				garbage.append(tile)
				del self.tile_by_pos[pos]
				del self.tile_reverse[tile]
		return garbage

	def new_tile(self, pos):
		print "new_tile", pos
		tile = clutter.CairoTexture.new(self.tile_size, self.tile_size)
		self.tile_group.add_actor(tile)
		tile.connect("draw", self.draw_cb)
		self.move_tile(tile, pos)
		tile.show()
		tile.invalidate()

	def move_tile(self, tile, pos):
		tile.set_position(pos[0], pos[1])
		self.tile_by_pos[pos] = tile
		self.tile_reverse[tile] = pos
		tile.invalidate()
			
	def draw_cb(self, tex, ctx, *rest):
		print "draw_cb", tex, ctx, rest
		tileid = self.tile_reverse.get(tex)
		pt_min = (tileid[0], tileid[1])
		pt_max = (pt_min[0] + self.tile_size, pt_min[1] + self.tile_size)
		if self.render_cb:
			self.render_cb(tex, ctx, pt_min, pt_max)

	def set_render_cb(self, cb):
		self.render_cb = cb
		for t in self.tile_reverse:
			t.invalidate()

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

	def draw_cb(self, texture, ctx, min_x, min_y, max_x, max_y):
		for curve in self.points:
			styler = self.style.get(curve)
			if styler is None:
				styler = self.style[curve] = MarkStyler()
			for p in self.points[curve]:
				pc = self.pt_pos(p)
				if pc[0] >= min_x and pc[0] <= max_x and pc[1] >= min_y and pc[1] <= max_y:
					styler.mark(ctxt, pc)
		ctxt.stroke()


if __name__ == "__main__":
	def render_cb(tex, ctx, pt_min, pt_max):
		ctx.set_source_rgb(0,0,0)
		ctx.move_to(0,25)
		ctx.show_text(str(pt_min))
		#print "DRAW:", tex, ctx, pt_min, pt_max
	
	import math
	import glib

	glib.threads_init()
	clutter.threads_init()
	clutter.init([])

	stg = clutter.Stage()
	stg.set_size(320, 240)
	
	q = Quilt(300, 220)
	q.set_render_cb(render_cb)
	q.show()

	stg.add_actor(q)
	stg.show()	

	q.set_viewport_scroll(200, 200)

	clutter.main()	

