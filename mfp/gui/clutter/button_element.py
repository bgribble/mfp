"""
clutter/button_element.py -- clutter backend for button elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

import math
from gi.repository import Clutter
import cairo

from mfp.utils import catchall
from ..colordb import ColorDB
from .base_element import ClutterBaseElementBackend
from ..button_element import (
    ButtonElement,
    ButtonElementImpl,
    BangButtonElement,
    BangButtonElementImpl,
    ToggleButtonElement,
    ToggleButtonElementImpl,
    ToggleIndicatorElement,
    ToggleIndicatorElementImpl,
)


def circle(ctx, xorig, yorig, w, h):
    w = w-1.0
    h = h-1.0
    ctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
    ctx.translate(xorig, yorig)
    ctx.arc(w/2.0, h/2.0, w/2.0, 0, 2*math.pi)
    ctx.close_path()


def rounded_box(ctx, xorig, yorig, w, h, rad):
    seg_h = h - 2 * rad
    seg_w = w - 2 * rad
    cdelta = rad / 2.0

    ctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
    ctx.translate(xorig, yorig)
    ctx.move_to(0, rad)
    ctx.line_to(0, rad + seg_h)
    ctx.curve_to(0, rad + seg_h + cdelta, cdelta, h, rad, h)
    ctx.line_to(rad + seg_w, h)
    ctx.curve_to(rad + seg_w + cdelta, h, w, h - rad + cdelta, w, h - rad)
    ctx.line_to(w, rad)
    ctx.curve_to(w, rad - cdelta, w - rad + cdelta, 0, w - rad, 0)
    ctx.line_to(rad, 0)
    ctx.curve_to(rad - cdelta, 0, 0, rad - cdelta, 0, rad)
    ctx.close_path()


class ClutterButtonElementImpl(ButtonElement, ButtonElementImpl, ClutterBaseElementBackend):
    backend_name = "clutter"

    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        # create elements
        self.texture = Clutter.Canvas.new()
        self.texture.connect("draw", self.draw_cb)

        self.group.set_content(self.texture)
        self.group.set_reactive(True)

        self.width = 20
        self.height = 20
        self.texture.set_size(self.width, self.height)
        self.group.set_size(self.width, self.height)
        self.group.set_position(x, y)

    def redraw(self):
        self.texture.invalidate()
        if self.indicator:
            self.label.set_color(self.get_color('text-color:lit'))
        else:
            self.label.set_color(self.get_color('text-color'))

    async def set_size(self, width, height):
        await super().set_size(width, height)
        self.texture.set_size(width, height)
        self.redraw()

    @catchall
    def draw_cb(self, texture, ct, width, height):
        w = width - 2
        h = height - 2

        c = ColorDB().normalize(self.get_color('stroke-color'))

        # Clear texture
        ct.save()
        ct.set_operator(cairo.OPERATOR_CLEAR)
        ct.paint()
        ct.restore()

        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)

        ct.set_line_width(1.5)
        ct.set_antialias(cairo.ANTIALIAS_NONE)

        # draw the box
        corner = max(2, 0.1*min(w, h))
        rounded_box(ct, 1, 1, w, h, corner)
        ct.stroke()

        # draw the indicator
        ioff = max(3, 0.075*min(w, h))
        iw = w - 2 * ioff
        ih = h - 2 * ioff
        rounded_box(ct, ioff, ioff, iw, ih, corner-1)

        c = ColorDB().normalize(self.get_color('fill-color:lit'))
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        if self.indicator:
            ct.fill()
        else:
            ct.stroke()

class ClutterBangButtonElementImpl(BangButtonElement, BangButtonElementImpl, ClutterButtonElementImpl):
    backend_name = "clutter"

class ClutterToggleButtonElementImpl(ToggleButtonElement, ToggleButtonElementImpl, ClutterButtonElementImpl):
    backend_name = "clutter"

class ClutterToggleIndicatorElementImpl(
    ToggleIndicatorElement, ToggleIndicatorElementImpl, ClutterButtonElementImpl
):
    @catchall
    def draw_cb(self, texture, ct, width, height):
        w = width - 2
        h = height - 2

        # clear texture
        ct.save()
        ct.set_operator(cairo.OPERATOR_CLEAR)
        ct.paint()
        ct.restore()

        c = ColorDB().normalize(self.get_color('stroke-color'))
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)

        ct.set_line_width(1.5)
        ct.set_antialias(cairo.ANTIALIAS_NONE)

        # draw the box
        circle(ct, 1, 1, w, h)
        ct.stroke()

        # draw the indicator
        ioff = max(3, 0.075*min(w, h))
        iw = w - 2 * ioff
        ih = h - 2 * ioff
        circle(ct, ioff, ioff, iw, ih)

        c = ColorDB().normalize(self.get_color('fill-color:lit'))
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        if self.indicator:
            ct.fill()
        else:
            ct.stiroke()
