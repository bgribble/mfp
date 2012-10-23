#! /usr/bin/env python
'''
quilt.py 
clutter widget supporting a tiled, viewport-oriented Cairo texture

Copyright (c) 2012 Bill Gribble <grib@billgribble.com> 
'''

from gi.repository import Clutter as clutter
from gi.repository import GObject
from mfp import log 
import gobject
import cairo
import math

class Quilt (clutter.Group):
	IDLE_INTERVAL = 500 
	VELOCITY_FUDGE = 1.25

	def __init__(self, width, height, tilesize=100):
		clutter.Group.__init__(self)
		self.set_clip(0, 0, width, height)

		self.viewport_width = width
		self.viewport_height = height

		self.viewport_x = 0
		self.viewport_y = 0
		self.viewport_vx = False
		self.viewport_vy = False

		self.viewport_x_base = 0
		self.viewport_y_base = 0

		self.tile_group = clutter.Group()
		self.tile_group.show()
		self.add_actor(self.tile_group)

		self.tile_animation = None
		self.tile_size = tilesize
		self.tile_by_pos = {}
		self.tile_reverse = {}

		self.render_cb = None

		self.rebuild_quilt()
		GObject.timeout_add(self.IDLE_INTERVAL, self.idle_cb)

	def set_viewport_scroll(self, vx, vy):
		if (vx != self.viewport_vx) or (vy != self.viewport_vy):
			self.viewport_vx = vx
			self.viewport_vy = vy

			self.reanimate()

	def set_viewport_origin(self, pos_x, pos_y, flush=False):
		self.tile_group.set_position(-pos_x, -pos_y)
		self.viewport_x = pos_x
		self.viewport_y = pos_y
		self.rebuild_quilt(flush)

	def get_viewport_origin(self):
		return (self.viewport_x, self.viewport_y)

	def set_size(self, width, height):
		self.viewport_width = width
		self.viewport_height = height
		clutter.Group.set_size(self, width, height)
		self.rebuild_quilt()

	def idle_cb(self, *args):
		pos = self.tile_group.get_position()
		self.viewport_x = -pos[0]
		self.viewport_y = -pos[1]
		self.rebuild_quilt()
		return True

	def reanimate(self, *args):
		target_x, target_y = self.tile_group.get_position()

		target_x -= 5*self.viewport_vx
		target_y -= 5*self.viewport_vy

		self.tile_animation = self.tile_group.animatev(clutter.AnimationMode.LINEAR, 5000,
													  ['x', 'y'],
													  [ target_x, target_y ])
		self.tile_animation.connect_after("completed", self.reanimate)

	def rebuild_quilt(self, flush=False):
		def lbound(val):
			return int(math.floor(val / float(self.tile_size)) * self.tile_size)

		def ubound(val):
			return lbound(val) + self.tile_size


		min_x = lbound(self.viewport_x)
		max_x = ubound(self.viewport_x + self.viewport_width)

		if self.viewport_vx < 0:
			min_x -= int(self.viewport_vx * self.VELOCITY_FUDGE)
		elif self.viewport_vx > 0:
			max_x += int(self.viewport_vx * self.VELOCITY_FUDGE)

		min_y = lbound(self.viewport_y)
		max_y = ubound(self.viewport_y + self.viewport_height)
	
		if self.viewport_vy < 0:
			min_y -= int(self.viewport_vy * self.VELOCITY_FUDGE)
		elif self.viewport_vy > 0:
			max_y += int(self.viewport_vy * self.VELOCITY_FUDGE)

		needed = {}
		for x in range(min_x, max_x, self.tile_size):
			for y in range(min_y, max_y, self.tile_size):
				needed[(x, y)] = True

		# alloc_tiles will kick off the redraw process
		self.alloc_tiles(needed, flush)

	def alloc_tiles(self, needed, flush=False):
		garbage = self.gc_tiles(needed)
		for pos in needed:
			tile = self.tile_by_pos.get(pos)
			if tile is None:
				if garbage:
					self.move_tile(garbage[0], pos)
					garbage = garbage[1:]
				else:
					self.new_tile(pos)
			elif flush:
				tile.clear()
				tile.invalidate()
		for tile in garbage: 
			tile.destroy()
		
	def gc_tiles(self, marked):
		garbage = []
		for pos, tile in self.tile_by_pos.items():
			if marked.get(pos) is None:
				garbage.append(tile)
				del self.tile_by_pos[pos]
				del self.tile_reverse[tile]
		return garbage

	def new_tile(self, pos):
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
		tile.clear()
		tile.invalidate()
			
	def redraw(self):
		# make sure tile allocation is correct
		self.rebuild_quilt()

	def clear(self):
		self.rebuild_quilt(flush=True)

	def draw_cb(self, tex, ctx, *rest):
		tileid = self.tile_reverse.get(tex)
		pt_min = (tileid[0], tileid[1])
		pt_max = (pt_min[0] + self.tile_size, pt_min[1] + self.tile_size)
		if self.render_cb:
			self.render_cb(tex, ctx, pt_min, pt_max)

	def set_render_cb(self, cb):
		self.render_cb = cb
		for t in self.tile_reverse:
			t.clear()
			t.invalidate()

