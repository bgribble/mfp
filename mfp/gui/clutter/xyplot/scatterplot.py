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
    def __init__(self, element, width, height):
        # data points
        self.points = {}
        self.points_by_tile = {}

        # roll-mode scroll speeds
        self.x_scroll = 0
        self.y_scroll = 0

        super().__init__(element, width, height)

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

        # if the viewport is animated (viewport_scroll not 0)
        # the position of the field may have changed.
        field_vp = self.plot.get_viewport_origin()
        field_vp_pos = self.px2pt(field_vp)
        field_w = self.x_max - self.x_min
        field_h = self.y_max - self.y_min

        if self.x_min != field_vp_pos[0]:
            self.x_min = field_vp_pos[0]
            self.x_max = self.x_min + field_w
            self._recalc_x_scale()

        if self.y_max != field_vp_pos[1]:
            self.y_max = field_vp_pos[1]
            self.y_min = self.y_max - field_h
            self._recalc_y_scale()

        for curve in self.points:
            curve = int(curve)
            styler = self.style.get(curve)
            if styler is None:
                log.warning("[scatterplot]: no style for curve", curve)
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
                    if styler.shape != "none":
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
        curve = int(curve)
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
            return (int(math.floor(point[0] / tile_size) * tile_size),
                    int(math.floor(point[1] / tile_size) * tile_size))

        px = self.pt2px(point)
        if px is None:
            # point is not legal, usually on log charts
            return []
        
        curve = int(curve)

        tiles = []
        pts = self.points.setdefault(curve, {})
        bytile = self.points_by_tile.setdefault(curve, {})

        style = self.style.get(curve)
        if style is None:
            style = self.style[curve] = MarkStyle()
        markradius = style.size

        for dx in [-markradius, markradius]:
            for dy in [-markradius, markradius]:
                x = px[0] + dx
                y = px[1] + dy
                tid = tile_id((x, y))
                if tid not in tiles:
                    tiles.append(tid)

        if style.stroke_style and ptnum > 0:
            prev_pt = pts[ptnum - 1][1]
            prev_px = self.pt2px(prev_pt)
            if prev_px is not None:
                tid = tile_id(prev_px)
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
            if curve in self.points:
                del self.points[curve]
            self.reindex()
        self.plot.clear()

    def set_style(self, style):
        for inlet, istyle in style.items():
            inlet = int(inlet)
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

    def save_style(self):
        sd = {}
        for inlet, style in self.style.items():
            props = sd.setdefault(str(inlet), {})
            props["size"] = style.size
            props["color"] = style.colorspec
            props["shape"] = style.shape
            props["stroke"] = style.stroke_style

        return sd


    async def configure(self, params):
        modes = dict(LINEAR=0, LOG=1, LOG_10=1, LOG_2=2)
        s = params.get("plot_style")
        if s:
            self.set_style(s)

        need_vp = False
        x = params.get("x_axis")
        if x:
            mode = modes.get(x.upper())
            if mode != self.x_axis_mode:
                self.x_axis_mode = mode
                self._recalc_x_scale()
                xax = self.pt2px((self.x_min, self.y_min))
                self.x_axis.set_viewport_origin(xax[0], 0, True)
                need_vp = True

        y = params.get("y_axis")
        if y:
            mode = modes.get(y.upper())
            if mode != self.y_axis_mode:
                self.y_axis_mode = mode
                self._recalc_y_scale()
                yax = self.pt2px((self.x_min, self.y_max))
                self.y_axis.set_viewport_origin(0, yax[1], True)
                need_vp = True

        if need_vp:
            origin = self.pt2px((self.x_min, self.y_max))
            self.set_field_origin(origin[0], origin[1], True)

    def set_field_origin(self, x_orig, y_orig, redraw):
        self.plot.set_viewport_origin(x_orig, y_orig, redraw)

    def command(self, action, data):
        if action == "add":
            for c in data:
                for p in data[c]:
                    self.append(p, c)
            return True
        elif action == "roll":
            self.set_bounds(None, None, data, None)
            self.set_scroll_rate(1.0, 0)
            return True
        elif action == "stop":
            self.set_scroll_rate(0.0, 0.0)
            return True
        elif action == "reset":
            self.set_bounds(None, None, data, None)
            return True

        return False
