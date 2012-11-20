#! /usr/bin/env python
'''
scatterplot.py 
Specialization of XYPlot for showing sets of discrete datapoints 

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import math

from .mark_style import MarkStyle
from .xyplot import XYPlot 
from mfp import log 


class ScatterPlot (XYPlot):
	def __init__(self, width, height):	
		# data points 
		self.points = {} 
		self.points_by_tile = {}

		# roll-mode scroll speeds 
		self.x_scroll = 0
		self.y_scroll = 0

		XYPlot.__init__(self, width, height)

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

		field_vp = self.plot.get_viewport_origin()
		field_vp_pos = self.px2pt(field_vp)
		field_w = self.x_max - self.x_min 
		field_h = self.y_max - self.y_min 

		self.x_min = field_vp_pos[0]
		self.x_max = self.x_min + field_w
		self.y_max = field_vp_pos[1]
		self.y_min = self.y_max - field_h

		for curve in self.points:
			styler = self.style.get(curve)
			if styler is None:
				styler = self.style[curve] = MarkStyle()

			tile_id = self.plot.tile_reverse.get(texture)
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

	def set_scroll_rate(self, vx, vy):
		px = self.pt2px((vx, vy))
		self.x_axis.set_viewport_scroll(px[0], 0)
		self.y_axis.set_viewport_scroll(0, px[1])
		self.plot.set_viewport_scroll(px[0], px[1])

	def append(self, point, curve=0):
		pts = self.points.setdefault(curve, [])
		ptnum = len(pts)
		pts.append([ptnum, point])

		tiles = self.index_point(point, curve, ptnum)
		for tile_id in tiles:
			tex = self.plot.tile_by_pos.get(tile_id)
			if tex is not None:
				tex.invalidate()


	def index_point(self, point, curve, ptnum):
		tile_size = self.plot.tile_size

		def tile_id(point):
			return (int(math.floor(point[0] / tile_size)*tile_size),
				int(math.floor(point[1] / tile_size)*tile_size))

		px = self.pt2px(point)

		tiles = []
		pts = self.points.setdefault(curve, {})
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
		self.plot.clear()

	def set_style(self, style):
		log.debug("ScatterPlot: updating style params", style)
		for inlet, istyle in style.items():
			marker = self.style.setdefault(inlet, MarkStyle()) 
			for k, v in istyle.items():
				if k == "size":
					marker.size = float(v)
				elif k == "color":
					marker.set_color(v)
				elif k == "shape":
					marker.shape = str(v)
				elif k == "stroke":
					marker.stroke_style = str(v)


