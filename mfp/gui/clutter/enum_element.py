"""
clutter/enum_element.py -- clutter backend for numeric/enumerated elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from gi.repository import Clutter
import cairo

from ..colordb import ColorDB
from .base_element import ClutterBaseElementImpl
from ..enum_element import (
    EnumElement,
    EnumElementImpl
)


class ClutterEnumElementImpl(EnumElementImpl, ClutterBaseElementImpl, EnumElement):
    backend_name = "clutter"

    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        # create elements
        self.texture = Clutter.Canvas.new()
        self.texture.connect("draw", self.draw_cb)
        self.group.set_content(self.texture)
        self.group.set_reactive(True)

        self.group.set_position(x, y)
        self.width = 35
        self.height = 25
        self.texture.set_size(self.width, self.height)
        self.group.set_size(self.width, self.height)

    def redraw(self):
        super().redraw()
        self.texture.invalidate()

    def draw_cb(self, texture, ct, width, height):
        lw = 2
        w = width - lw
        h = height - lw

        # clear the drawing area
        ct.save()
        ct.set_operator(cairo.OPERATOR_CLEAR)
        ct.paint()
        ct.restore()

        ct.set_line_width(lw)
        ct.set_antialias(cairo.ANTIALIAS_NONE)
        if self.obj_state == self.OBJ_COMPLETE:
            ct.set_dash([])
        else:
            ct.set_dash([8, 4])

        ct.translate(lw/2.0, lw/2.0)
        ct.move_to(0, 0)
        ct.line_to(0, h)
        ct.line_to(w, h)
        ct.line_to(w, h / 3.0)
        ct.line_to(w - h / 3.0, 0)
        ct.line_to(0, 0)
        ct.close_path()

        color = ColorDB().normalize(self.get_color('fill-color'))
        ct.set_source_rgba(color.red, color.green, color.blue, 1.0)
        ct.fill_preserve()

        color = ColorDB().normalize(self.get_color('stroke-color'))
        ct.set_source_rgba(color.red, color.green, color.blue, 1.0)
        ct.stroke()

    async def set_size(self, width, height, **kwargs):
        await super().set_size(width, height, **kwargs)

        self.texture.set_size(width, height)
        self.texture.invalidate()

    def port_position(self, port_dir, port_num):
        # tweak the right input port display to be left of the slant
        if port_dir == BaseElement.PORT_IN and port_num == 1:
            default = BaseElement.port_position(self, port_dir, port_num)
            return (default[0] - self.PORT_TWEAK, default[1])
        else:
            return BaseElement.port_position(self, port_dir, port_num)

