#! /usr/bin/env python
'''
xyplot.py 
clutter widget supporting scatter, line, and roll plots

Copyright (c) 2012 Bill Gribble <grib@billgribble.com> 
'''

from gi.repository import Clutter as clutter
import glib
import gobject
import cairo
import math

from .mark_style import MarkStyle
from .quilt import Quilt 

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

class XYPlot (clutter.Group):
	MARGIN_LEFT = 30 
	MARGIN_BOT = 30
	AXIS_PAD = 5
	TICK_SIZE = 50

	SCATTER = 0
	CURVE = 1

	def __init__(self, width, height):
		clutter.Group.__init__(self)

		self.width = width
		self.height = height

		self.points = {} 
		self.points_by_tile = {}
		self.style = {}

		# scaling params
		self.x_min = 0
		self.x_max = 6.28 
		self.y_min = -1
		self.y_max = 1
		self.x_scroll = 0
		self.y_scroll = 0
		self.axis_font_size = 8

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
		self.cl_bg = clutter.Rectangle()
		self.cl_bg.set_border_width(0)
		self.cl_bg.set_border_color(black)
		self.cl_bg.set_color(white)
		self.cl_bg.set_size(self.width, self.height)
		self.cl_bg.set_position(0,0)
		self.add_actor(self.cl_bg)
		
		self.cl_field_w = self.width - self.MARGIN_LEFT
		self.cl_field_h = self.height - self.MARGIN_BOT

		self.cl_xaxis_bg = Quilt(self.cl_field_w, self.MARGIN_BOT)
		self.cl_xaxis_bg.set_position(self.MARGIN_LEFT, self.height-self.MARGIN_BOT)
		self.cl_xaxis_bg.set_viewport_origin(0, 0)
		self.add_actor(self.cl_xaxis_bg)

		self.cl_yaxis_bg = Quilt(self.MARGIN_LEFT, self.cl_field_h)
		self.cl_yaxis_bg.set_position(0, 0)
		self.cl_yaxis_bg.set_viewport_origin(0, -self.cl_field_h/2.0)
		self.add_actor(self.cl_yaxis_bg)

		self.cl_xaxis_bg.set_render_cb(self.draw_xaxis_cb)
		self.cl_yaxis_bg.set_render_cb(self.draw_yaxis_cb)

		self.cl_field = clutter.Rectangle()
		self.cl_field.set_border_width(0)
		self.cl_field.set_border_color(black)
		self.cl_field.set_color(white)
		self.cl_field.set_size(self.cl_field_w, self.cl_field_h)
		self.cl_field.set_position(self.MARGIN_LEFT, 0)

		self.add_actor(self.cl_field)

		self.cl_curve = Quilt(self.cl_field_w, self.cl_field_h)
		self.cl_curve.set_position(self.MARGIN_LEFT, 0)
		self.cl_curve.set_render_cb(self.draw_field_cb)
		self.cl_curve.set_viewport_origin(0, -self.cl_field_h/2.0)
		self.add_actor(self.cl_curve)
		
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

		self.cl_xaxis_bg.redraw()
		self.cl_yaxis_bg.redraw()
		self.cl_curve.redraw()

	def set_scroll_rate(self, vx, vy):
		px = self.pt2px((vx, vy))
		self.cl_xaxis_bg.set_viewport_scroll(px[0], 0)
		self.cl_yaxis_bg.set_viewport_scroll(0, px[1])
		self.cl_curve.set_viewport_scroll(px[0], px[1])

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

		print "XYPlot.set_bounds:", x_min, y_min, x_max, y_max

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
			self.cl_xaxis_bg.set_viewport_origin(origin[0], origin[1], need_x_flush)

		if ((y_min != self.y_min) or (y_max != self.y_max)):
			self.y_min = y_min
			self.y_max = y_max
			origin = self.pt2px((0, y_max))
			self.cl_yaxis_bg.set_viewport_origin(origin[0], origin[1], need_y_flush)

		origin = self.pt2px((x_min, y_max))
		if need_x_flush or need_y_flush:
			self.reindex()

		self.cl_curve.set_viewport_origin(origin[0], origin[1], need_x_flush or need_y_flush)

	def set_style(self, style):
		for inlet, istyle in style.items():
			marker = self.style.setdefault(inlet, MarkStyle()) 
			for k, v in istyle.items():
				if k == "size":
					marker.size = float(v)
				elif k == "color":
					marker.set_color(v)
				elif k == "shape":
					marker.shape = str(v)
				elif k == "stroke_style":
					marker.stroke_style = str(v)

	def pt_pos(self, p):
		np = [(p[0] - self.x_min)*float(self.cl_field_w)/(self.x_max - self.x_min),
		      self.cl_field_h - (p[1] - self.y_min)*float(self.cl_field_h)/(self.y_max - self.y_min)]
		return np

	def pt2px(self, p):
		np = [p[0]*float(self.cl_field_w)/(self.x_max - self.x_min),
		      -1.0*p[1]*float(self.cl_field_h)/(self.y_max - self.y_min)]
		return np

	def px2pt(self, p):
		np = [p[0]/(float(self.cl_field_w)/(self.x_max - self.x_min)),
		      -1.0*p[1]/(float(self.cl_field_h)/(self.y_max - self.y_min))]
		return np

	def draw_xaxis_cb(self, texture, ctx, px_min, px_max):
		print "XYPlot.draw_xaxis_cb:", px_min, px_max
		pt_min = self.px2pt(px_min)
		pt_max = self.px2pt(px_max)

		# X axis
		ticks = mkticks(self.x_min, self.x_max, self.cl_field_w/self.TICK_SIZE)
		ctx.set_source_rgb(black.red, black.green, black.blue)
		ctx.set_font_size(self.axis_font_size)

		# the axis line
		ctx.move_to(0, self.AXIS_PAD)
		ctx.line_to(texture.get_width(), self.AXIS_PAD)
		ctx.stroke()

		print "xaxis: drawing ticks", ticks
		# ticks
		for tick in ticks:
			print "tick:", tick
			tick_px = self.pt2px((tick, 0))
			if (tick_px[0] < (px_min[0] - self.MARGIN_LEFT) or tick_px[0] > (px_max[0]+self.MARGIN_LEFT)):
				print "skipping", tick_px, px_min, px_max, self.MARGIN_LEFT
				continue

			p = self.pt_pos([tick, 0])
			ctx.move_to(tick_px[0]-px_min[0], self.AXIS_PAD)
			ctx.line_to(tick_px[0]-px_min[0], 3*self.AXIS_PAD)
			ctx.stroke()
			ctx.move_to(tick_px[0]-px_min[0], self.MARGIN_BOT-self.AXIS_PAD)
			ctx.show_text("%.3g" % tick)

	def draw_yaxis_cb(self, texture, ctx, px_min, px_max):
		pt_min = self.px2pt(px_min)
		pt_max = self.px2pt(px_max)

		# Y axis ticks
		ticks = mkticks(self.y_min, self.y_max, float(self.cl_field_h)/self.TICK_SIZE)
		ctx.set_source_rgb(black.red, black.green, black.blue)
		ctx.set_font_size(self.axis_font_size)
		
		# the axis line
		ctx.move_to(self.MARGIN_LEFT - self.AXIS_PAD, 0)
		ctx.line_to(self.MARGIN_LEFT - self.AXIS_PAD, texture.get_height())
		ctx.stroke()

		# ticks
		for tick in ticks:
			tick_px = self.pt2px((0,tick))
			if (tick_px[1] < (px_min[1] - self.MARGIN_BOT) or tick_px[1] > (px_max[1]+self.MARGIN_BOT)):
				continue

			ctx.move_to(self.MARGIN_LEFT-self.AXIS_PAD, tick_px[1]-px_min[1])
			ctx.line_to(self.MARGIN_LEFT-3*self.AXIS_PAD, tick_px[1]-px_min[1])
			ctx.stroke()
			ctx.save()
			ctx.move_to(self.AXIS_PAD, tick_px[1]-px_min[1])
			ctx.rotate(math.pi/2)
			ctx.show_text("%.3g" % tick)
			ctx.restore()

	def draw_field_cb(self, texture, ctxt, px_min, px_max):
		def stroke_to(styler, curve, px, ptnum, delta):
			points = self.points.get(curve)
			dst_ptnum = ptnum + delta
			if dst_ptnum < 0 or dst_ptnum > points[-1][0]:
				return
			dst_num, dst_pt = points[dst_ptnum]
			dst_px = self.pt2px(dst_pt)
			dst_px[0] -= px_min[0]
			dst_px[1] -= px_min[1]
			styler.stroke(ctxt, dst_px, px)

		field_vp = self.cl_curve.get_viewport_origin()
		field_vp_pos = self.px2pt(field_vp)
		field_w = self.x_max - self.x_min 
		field_h = self.y_max - self.y_min 

		self.x_min = field_vp_pos[0]
		self.x_max = self.x_min + field_w
		self.y_max = field_vp_pos[1]
		self.y_min = self.y_max - field_h

		print "draw_field_cb: set min, max to (%s, %s), (%s, %s)" % (self.x_min, self.y_min,
															   self.x_max, self.y_max)


		for curve in self.points:
			styler = self.style.get(curve)
			if styler is None:
				styler = self.style[curve] = MarkStyle()

			tile_id = self.cl_curve.tile_reverse.get(texture)
			if tile_id is None:
				return

			points = self.points_by_tile[curve].get(tile_id)	
			if points is not None:	
				for ptnum, p in points:
					pc = self.pt2px(p)
					pc[0] -= px_min[0]
					pc[1] -= px_min[1]
					styler.mark(ctxt, pc)
					if styler.stroke_style:
						stroke_to(styler, curve, pc, ptnum, -1)
				if styler.stroke_style:
					ptnum, p = points[-1]
					pc = self.pt2px(p)
					pc[0] -= px_min[0]
					pc[1] -= px_min[1]	
					stroke_to(styler, curve, pc, ptnum, 1)

	def append(self, point, curve=0):
		pts = self.points.setdefault(curve, [])
		ptnum = len(pts)
		pts.append([ptnum, point])

		tiles = self.index_point(point, curve, ptnum)
		for tile_id in tiles:
			tex = self.cl_curve.tile_by_pos.get(tile_id)
			if tex is not None:
				tex.invalidate()


	def index_point(self, point, curve, ptnum):
		tile_size = self.cl_curve.tile_size

		def tile_id(point):
			return (int(math.floor(point[0] / tile_size)*tile_size),
				int(math.floor(point[1] / tile_size)*tile_size))

		px = self.pt2px(point)

		tiles = []

		bytile = self.points_by_tile.setdefault(curve, {})
		
		style = self.style.get(curve)
		if style is None:
			style = self.style[curve] = MarkStyle()
		markradius = style.size

		for dx in [-markradius, markradius ]:
			for dy in [-markradius, markradius]:
				x = px[0] + dx
				y = px[1] + dy
				tid = tile_id((x,y))
				if tid not in tiles:
					tiles.append(tid)

		if style.stroke_style and ptnum > 0:
			prev_pt = pts[ptnum-1][1]
			tid = tile_id(self.pt2px(prev_pt))
			if tid not in tiles:
				tiles.append(tid)

		for tile_id in tiles:
			pts = bytile.setdefault(tile_id, [])
			pts.append([ptnum, point])

		return tiles 


	def reindex(self):
		self.points_by_tile = {} 
		for curve, curvepoints in self.points.items():
			for ptnum, point in curvepoints:
				self.index_point(point, curve, ptnum)
		
	def clear(self, curve=None):
		if curve is None:
			self.points = {}
			self.points_by_tile = {} 
		elif curve is not None:
			if self.points.has_key(curve):
				del self.points[curve]
			self.reindex()	
		self.cl_curve.clear()


if __name__ == "__main__":
	import math
	import glib

	glib.threads_init()
	clutter.threads_init()
	clutter.init([])

	stg = clutter.Stage()
	stg.set_size(600, 400)

	x = XYPlot(600, 400)
	x.set_style({0: dict(stroke_style="solid")})
	x.show()
	stg.add_actor(x)
	stg.show()	

	for p in range(0, 70):
		x.append((p/10.0, math.sin(p/10.0)))

	clutter.main()	

