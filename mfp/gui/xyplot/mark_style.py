#! /usr/bin/env python
'''
mark_style.py
Helper class to save style info and render a styled mark/stroke

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter as clutter
import math


class MarkStyle (object):
    SQRT_3 = 3.0 ** 0.5

    def __init__(self):
        self.col_r = 0
        self.col_g = 0
        self.col_b = 0
        self.col_a = 255
        self.colorspec = (0,0,0,255)
        self.shape = "dot"
        self.size = 1.0
        self.stroke_style = None
        self.fill = True
        self.size_elt = None
        self.alpha_elt = None

    def set_color(self, newcolor):
        r = g = b = 0
        a = 1.0

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
        self.colorspec = newcolor

    def mark_dot(self, ctx, point):
        ctx.move_to(point[0] + self.size, point[1])
        ctx.arc(point[0], point[1], self.size, 0.0, math.pi * 2.0)

    def mark_square(self, ctx, point):
        dx = self.size / 2.0
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

    def stroke(self, ctx, pt_1, pt_2):
        def halfbrite(c):
            return c + (1.0 - c) / 2.0

        if self.stroke_style == "solid":
            ctx.set_source_rgba(halfbrite(self.col_r), halfbrite(self.col_g),
                                halfbrite(self.col_b), self.col_a)
            ctx.set_line_width(0.3)
            ctx.move_to(pt_1[0], pt_1[1])
            ctx.line_to(pt_2[0], pt_2[1])
            ctx.stroke()

    def mark(self, ctx, point):
        ctx.set_source_rgba(self.col_r, self.col_g, self.col_b, self.col_a)
        ctx.set_line_width(0.6)
        if self.shape == "dot":
            self.mark_dot(ctx, point)
        elif self.shape == "square":
            self.mark_square(ctx, point)
        elif self.shape == "triangle":
            self.mark_triangle(ctx, point)
        ctx.stroke()
