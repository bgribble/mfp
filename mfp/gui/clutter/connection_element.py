"""
clutter/connection_element.py -- clutter backend for connection elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""
import math

from gi.repository import Clutter
import cairo

from ..colordb import ColorDB
from ..base_element import BaseElement
from .base_element import ClutterBaseElementBackend
from ..connection_element import (
    ConnectionElement,
    ConnectionElementImpl,
)


class ClutterConnectionElementImpl(ConnectionElement, ConnectionElementImpl, ClutterBaseElementBackend):
    backend_name = "clutter"

    def __init__(self, window, obj_1, port_1, obj_2, port_2, dashed=False):
        super().__init__(window, obj_1, port_1, obj_2, port_2, dashed)

        self.texture = Clutter.Canvas.new()
        self.group.set_content(self.texture)
        self.texture.connect("draw", self.draw_cb)

        self.group.set_reactive(True)
        if self.obj_1.layer is not None:
            self.move_to_layer(self.obj_1.layer)
        elif self.obj_2.layer is not None:
            self.move_to_layer(self.obj_2.layer)

        self.set_size(15, 15)

        px, py = self.obj_1.get_position()
        self.move(px, py)
        self.draw()

    async def delete(self):
        if self.texture:
            self.group.set_content(None)
            self.texture = None

        await super().delete()

    def redraw(self):
        super().redraw()
        self.draw()

    def draw(self):
        if self.obj_1 is None or self.obj_2 is None:
            return

        p1 = self.obj_1.port_center(BaseElement.PORT_OUT, self.port_1)
        p2 = self.obj_2.port_center(BaseElement.PORT_IN, self.port_2)

        if self.dsp_connect is True:
            self.width = 2.5 * self.LINE_WIDTH
        else:
            self.width = 1.5 * self.LINE_WIDTH
        self.height = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
        theta = math.atan2(p1[0] - p2[0], p2[1] - p1[1])
        self.rotation = theta * 180.0 / math.pi
        self.position_x = p1[0] - math.cos(theta) * self.width / 2.0
        self.position_y = p1[1] - math.sin(theta) * self.width / 2.0

        self.set_position(self.position_x, self.position_y)
        self.group.set_rotation(Clutter.RotateAxis.Z_AXIS, self.rotation, 0, 0, 0)

        self.set_size(math.ceil(self.width), math.ceil(self.height))
        self.texture.invalidate()


    def draw_cb(self, texture, ctx, width, height):
        # clear the drawing area
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()
        ctx.restore()

        ctx.set_operator(cairo.OPERATOR_OVER)
        ctx.set_antialias(cairo.ANTIALIAS_NONE)

        if self.dsp_connect:
            lw = 2.0 * self.LINE_WIDTH
        else:
            lw = self.LINE_WIDTH
        ctx.set_line_width(lw)

        if self.dashed:
            ctx.set_dash([4, 4])
        else:
            ctx.set_dash([])

        ctx.translate(width/2.0, lw/2.0)
        ctx.move_to(0, 0)
        ctx.line_to(0, height)
        ctx.close_path()

        c = ColorDB().normalize(self.get_color('stroke-color'))
        ctx.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        ctx.stroke()
        return True

    def draw_ports(self):
        pass

    def set_size(self, width, height):
        super().set_size(width, height)
        self.texture.set_size(width, height)
        self.texture.invalidate()

    def move(self, x, y):
        self.position_x = x
        self.position_y = y

        self.group.set_position(x, y)

    def corners(self):
        if self.obj_1 and self.obj_2:
            p1 = self.obj_1.port_center(BaseElement.PORT_OUT, self.port_1)
            p2 = self.obj_2.port_center(BaseElement.PORT_IN, self.port_2)
            return [p1, p2]
        return None
