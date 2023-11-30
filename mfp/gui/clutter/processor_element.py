"""
clutter/processor_element.py -- clutter backend for processor elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from gi.repository import Clutter
import cairo

from mfp import log
from ..colordb import ColorDB
from .base_element import ClutterBaseElementBackend
from ..processor_element import (
    ProcessorElement,
    ProcessorElementImpl,
)


class ClutterProcessorElementImpl(ProcessorElement, ProcessorElementImpl, ClutterBaseElementBackend):
    backend_name = "clutter"

    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        # create elements
        self.texture = Clutter.Canvas.new()
        self.texture.connect("draw", self.draw_cb)
        self.group.set_content(self.texture)
        self.group.set_reactive(True)

        # resize widget whne text gets longer
        self.label.signal_listen('text-changed', self.label_changed_cb)
        self.set_size(35, 25)
        self.move(x, y)

        self.redraw()

    def redraw(self):
        super().redraw()
        self.texture.invalidate()

    def set_size(self, width, height):
        super().set_size(width, height)
        self.texture.set_size(width, height)

    def label_changed_cb(self, *args):
        newtext = self.label.get_text()
        if newtext != self.label_text:
            self.label_text = newtext
            self.update()

    def select(self):
        super().select()
        self.label.set_color(self.get_color('text-color'))
        self.texture.invalidate()

    def unselect(self):
        super().unselect()
        self.label.set_color(self.get_color('text-color'))
        self.texture.invalidate()

    def draw_cb(self, texture, ct, width, height):
        lw = 2.0

        w = width - lw
        h = height - lw

        # clear the drawing area
        ct.save()
        ct.set_operator(cairo.OPERATOR_CLEAR)
        ct.paint()
        ct.restore()

        ct.set_line_width(lw)
        ct.set_antialias(cairo.ANTIALIAS_NONE)
        ct.translate(lw/2.0, lw/2.0)
        ct.move_to(0, 0)
        ct.line_to(0, h)
        ct.line_to(w, h)
        ct.line_to(w, 0)
        ct.line_to(0, 0)
        ct.close_path()

        # fill to paint the background
        color = ColorDB().normalize(self.get_color('fill-color'))
        ct.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        ct.fill_preserve()

        # stroke to draw the outline
        color = ColorDB().normalize(self.get_color('stroke-color'))
        ct.set_source_rgba(color.red, color.green, color.blue, color.alpha)

        if self.obj_state == self.OBJ_COMPLETE:
            ct.set_dash([])
        else:
            ct.set_dash([8, 4])
        ct.set_line_width(lw)
        ct.stroke()
        return True
