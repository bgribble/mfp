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
	# possible arrangements of 4 tiles
	# 01_23 means [[0, 1], [2, 3]] 
	CONF_01_23 = 0
	CONF_10_32 = 1
	CONF_23_01 = 2
	CONF_32_10 = 3

	# map (config, tile) to offsets from upper left as multiples
	# of (w,h)
	_deltamap = {
		(CONF_01_23, 0): (0, 0), (CONF_01_23, 1): (1, 0), 
		(CONF_01_23, 2): (0, 1), (CONF_01_23, 3): (1, 1), 
		(CONF_10_32, 0): (1, 0), (CONF_10_32, 1): (0, 0), 
		(CONF_10_32, 2): (1, 1), (CONF_10_32, 3): (0, 1), 
		(CONF_23_01, 0): (0, 1), (CONF_23_01, 1): (1, 1), 
		(CONF_23_01, 2): (0, 0), (CONF_23_01, 3): (1, 0), 
		(CONF_32_10, 0): (1, 1), (CONF_32_10, 1): (0, 1), 
		(CONF_32_10, 2): (1, 0), (CONF_32_10, 3): (0, 0)
	}

	# map (config, key, tile) to offsets from upper-left of key tile
	# as multiples of (w,h)
	_from_key = {
		(0,0,1): (1,0), (0,0,2): (0,1), (0,0,3): (1,1), (0,3,0): (-1,-1),
		(0,3,1): (0,-1), (0,3,2): (-1,0), (1,0,1): (-1,0), (1,0,2): (0,1),
		(1,0,3): (-1,1), (1,3,0): (1,-1), (1,3,1): (0,-1), (1,3,2): (-1,0),
		(2,0,1): (1,0), (2,0,2): (0,-1), (2,0,3): (1,-1), (2,3,0): (-1,1),
		(2,3,1): (0,1), (2,3,2): (-1,0), (3,0,1): (-1,0), (3,0,2): (0,-1),
		(3,0,3): (-1,-1), (3,3,0): (1,1), (3,3,1): (0,1), (3,3,2): (1,0)
	}

	# map (config, key) to bounding points of quilt, as displacements
	# from origin of key tile
	_boundsmap = {
		(CONF_01_23, 0): (0, 0, 2, 2), (CONF_01_23, 3): (-1, -1, 1, 1),
		(CONF_10_32, 0): (-1, 0, 1, 2), (CONF_10_32, 3): (0, -1, 1, 1),
		(CONF_23_01, 0): (0, -1, 2, 1), (CONF_23_01, 3): (-1, 0, 1, 2),
		(CONF_32_10, 0): (-1, -1, 1, 1), (CONF_32_10, 3): (0, 0, 2, 2)
	}

	def __init__(self, w, h):
		clutter.Group.__init__(self)
		self.set_clip(0, 0, w, h)

		self.width = w
		self.height = h
		self.origin_x = 0
		self.origin_y = 0

		self.tile_configuration = self.CONF_01_23
		self.tile_key = 0
		self.tile_w = 1.5 * w
		self.tile_h = 1.5 * h

		self.rectangle = clutter.Rectangle()
		
		self.tiles = [ clutter.CairoTexture.new(self.tile_w, self.tile_h) for n in [0,1,2,3]]
		self.tiles_reverse = { self.tiles[0]: 0, self.tiles[1]: 1, self.tiles[2]: 2, self.tiles[3]: 3}

		self.scroll_vx = False
		self.scroll_vy = False

		self.rectangle.set_size(w, h)
		self.rectangle.set_border_width(1)
		self.rectangle.set_border_color(black)
		self.rectangle.set_position(0,0)
		self.rectangle.set_depth(-1)
		self.add_actor(self.rectangle)

		for tnum in [0,1,2,3]:
			self.add_actor(self.tiles[tnum])
			self.tiles[tnum].connect("draw", self.draw_cb)

		self.tiles[0].set_position(-0.25 * w, -0.25*h)
		self.constrain_tiles(self.tile_configuration, self.tile_key)

		for tnum in [0,1,2,3]:
			self.tiles[tnum].invalidate()
			
	def draw_cb(self, tex, ctx):
		tilenum = self.tiles_reverse.get(tex)
		tile_x, tile_y = self.get_tile_position(tilenum)

		# is it ok to emit "draw" on parent?
		if self.render_cb:
			self.render_cb(tex, ctx, tile_x, tile_y, tile_x+self.tile_w, tile_y + self.tile_h)

	def constrain_tiles(self, configuration, key_tile):
		for t in self.tiles:
			t.clear_constraints()

		w = self.tile_w
		h = self.tile_h

		if configuration == Quilt.CONF_01_23:
			self.constrain_tiles_with_offsets([w, 0, 0, h, 0, -w, -h, 0], key_tile)
		elif configuration == Quilt.CONF_10_32:
			self.constrain_tiles_with_offsets([-w, 0, 0, h, 0, w, -h, 0], key_tile)
		elif configuration == Quilt.CONF_23_01:
			self.constrain_tiles_with_offsets([w, 0, 0, -h, 0, -w, h, 0], key_tile)
		elif configuration == Quilt.CONF_32_10:
			self.constrain_tiles_with_offsets([-w, 0, 0, -h, 0, w, h, 0], key_tile)
		else:
			print "constrain_tiles: configuration ", configuration, "does not exist"
			# error
			pass
		self.tile_configuration = configuration
		self.tile_key = key_tile

	def constrain_tiles_with_offsets(self, offsets, key_tile):
		if key_tile == 0:
			cx1 = clutter.bind_constraint_new(self.tiles[0], clutter.BindCoordinate.X,
											  offsets[0])
			cx2 = clutter.bind_constraint_new(self.tiles[0], clutter.BindCoordinate.X,
									          offsets[1])
			cy1 = clutter.bind_constraint_new(self.tiles[0], clutter.BindCoordinate.Y, 
									          offsets[2])
			cy2 = clutter.bind_constraint_new(self.tiles[0], clutter.BindCoordinate.Y,
											  offsets[3])

			self.tiles[3].add_constraint(cx1)
			self.tiles[3].add_constraint(cy2)
		else:
			cx1 = clutter.bind_constraint_new(self.tiles[3], clutter.BindCoordinate.X,
									          offsets[4])
			cx2 = clutter.bind_constraint_new(self.tiles[3], clutter.BindCoordinate.X,
											  offsets[5])
			cy1 = clutter.bind_constraint_new(self.tiles[3], clutter.BindCoordinate.Y,
											  offsets[6])
			cy2 = clutter.bind_constraint_new(self.tiles[3], clutter.BindCoordinate.Y, 
									          offsets[7])

			self.tiles[0].add_constraint(cx1)
			self.tiles[0].add_constraint(cy1)
			
		self.tiles[1].add_constraint(cx1)
		self.tiles[1].add_constraint(cy1)
		self.tiles[2].add_constraint(cx2)
		self.tiles[2].add_constraint(cy2)

	def get_tile_offset(self, tile):
		'''
		Return (x,y) delta from origin of key tile to origin 
		of target tile in current configuration
		'''

		key = (self.tile_configuration, tile)
		signs = self._deltamap.get(key)
		return (signs[0]*self.tile_width, signs[1]*self.tile_height)

	def get_tile_position(self, tile):
		origin_off = self.get_tile_offset(tile)
		return (origin_off[0] + self.origin_x, origin_off[1]+self.origin_y)

	def get_bounds(self):
		''' 
		Return min and max points of quilt if frame of ref of
		viewport
		'''

		key_x, key_y = self.tiles[self.tile_key].get_position()
		off_min_x, off_min_y, off_max_x, off_max_y = self._boundsmap.get((self.tile_configuration,
																	      self.tile_key))
		w = self.tile_width
		h = self.tile_height
		return (key_x + off_min_x * w, key_x + off_min_y * h, 
		        key_x + off_max_x * w, key_x + off_max_y * h)

	def next_tile_configuration(self):
		OK=0 ; BAD=1
		
		# min/max points of quilt canvas area
		min_x, min_y, max_x, max_y = self.get_bounds()

		edge_left = edge_right = edge_top = edge_bottom = overlap = OK
		next_configuration = self.tile_configuration
		next_key = self.tile_key

		if ((self.scroll_vx < 0 and min_x >= (-0.25 * self.width))
		    or (min_x >= 0)):
			edge_left = BAD

		if ((self.scroll_vx > 0 and max_x <= (1.25 * self.width))
	        or (max_x <= self.width)):
			edge_right = BAD

		if ((self.scroll_vy < 0 and min_y >= (-0.25 * self.height))
	        or (min_y >= 0)):
			edge_top = BAD

		if ((self.scroll_vy > 0 and max_y <= (1.25 * self.height))
	        or (max_y <= self.height)):
			edge_bottom = BAD

		if ((min_x >= self.width) or (max_x <= 0) 
	        or (min_y >= self.height) or (max_y <= 0)):
			overlap = BAD
		
		bad_edges = edge_top + edge_bottom + edge_left + edge_right

		if overlap == BAD:
			pass
		elif bad_edges == 0:
			pass
		elif bad_edges == 1:
			pass

		elif bad_edges == 2:
			pass
		else:
			# error -- should never happen
			pass 

		return (next_configuration, next_key)

	def anim_complete_cb(self, animation, tex):
		# are we still animating?  if not, bail
		if self.scroll_vx is None and self.scroll_vy is None:
			return

		# do we need to reconfigure?
		newconf, newkey = self.next_tile_configuration()
		if newconf != self.tile_configuration or newkey != self.tile_key:
			# configure tiles
			self.configure_tiles(newconf, newkey)

		# use scrolling speeds to compute new animation target
		anim_time, anim_x, anim_y = self.next_animation_target()

		# call the implicit animation
		a2 = self.tiles[self.tile_key].animatev(clutter.AnimationMode.LINEAR, 
											       anim_time, ["x", "y"], [anim_x, anim_y])

		# add the callback 
		a2.connect_after("completed", self.anim_complete_cb)


		#### junk #########################
		tnum = args[-1]
		anim_x = -1.75 * self.width
		anim_time_1 = 3.0*self.width/self.timescale
		self.tiles[1].set_position(1.25 * self.width, 0.25*self.height)
		a2 = self.tiles[1].animatev(clutter.AnimationMode.LINEAR, anim_time_1, ["x"], [anim_x])
		a2.connect_after("completed", self.tile_1_cb)
		print "tile_1_cb"

	def set_autoscroll(self, rate_x, rate_y=False):
		if self.scroll_vx is not None or self.scroll_vy is not None:
			need_reset = True
		else:
			need_reset = False

		self.scroll_vx = rate_x
		self.scroll_vy = rate_y

		anim = self.tiles[self.tile_key].get_animation()

		# calling set_completed() will cause CB to be called
		if anim is not None:
			anim.set_completed()
		else:
			self.anim_complete_cb(tnum)


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

