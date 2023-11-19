"""
clutter/text_element.py -- clutter backend for text (comment) elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from gi.repository import Clutter
import cairo

from mfp.utils import catchall
from ..colordb import ColorDB
from .base_element import ClutterBaseElementBackend
from ..text_element import (
    TextElement,
    TextElementImpl
)


class ClutterTextElementImpl(TextElement, TextElementImpl, ClutterBaseElementBackend):
    backend_name = "clutter"

    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        self.texture = Clutter.Canvas.new()
        self.texture.connect("draw", self.draw_cb)
        self.group.set_content(self.texture)

        self.update_required = True
        self.move(x, y)
        self.set_size(12, 12)
        self.group.set_reactive(True)

    def redraw(self):
        self.texture.invalidate()
        self.draw_ports()

    @catchall
    def draw_cb(self, texture, ct, width, height):
        # clear the drawing area
        ct.save()
        ct.set_operator(cairo.OPERATOR_CLEAR)
        ct.paint()
        ct.restore()

        # fill to paint the background
        color = ColorDB().normalize(self.get_color('fill-color'))
        ct.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        ct.rectangle(0, 0, width, height)
        ct.fill()

        if self.clickchange or self.get_style('border'):
            ct.set_line_width(1.0)
            ct.translate(0.5, 0.5)
            ct.set_antialias(cairo.ANTIALIAS_NONE)
            ct.rectangle(0, 0, width-1, height-1)
            color = ColorDB().normalize(self.get_color('border-color'))
            ct.set_source_rgba(color.red, color.green, color.blue, color.alpha)
            ct.stroke()
        return True

    def set_size(self, width, height):
        super().set_size(width, height)

        self.texture.set_size(width, height)
        self.texture.invalidate()
