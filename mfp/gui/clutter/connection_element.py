"""
clutter/connection_element.py -- clutter backend for connection elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""
import math

from gi.repository import Clutter
import cairo

from ..colordb import ColorDB
from ..base_element import BaseElement
from .base_element import ClutterBaseElementImpl
from ..connection_element import (
    ConnectionElement,
    ConnectionElementImpl,
)


class ClutterConnectionElementImpl(ConnectionElementImpl, ClutterBaseElementImpl, ConnectionElement):
    backend_name = "clutter"

    def __init__(self, window, position_x, position_y):
        super().__init__(window, position_x, position_y)

        self.texture = Clutter.Canvas.new()
        self.group.set_content(self.texture)
        self.texture.connect("draw", self.draw_cb)

        self.group.set_reactive(True)
        self.width = 15
        self.height = 15
        self.texture.set_size(self.width, self.height)

    async def update(self):
        await self.draw()

    async def delete(self, **kwargs):
        if self.texture:
            self.group.set_content(None)
            self.texture = None

        await super().delete(**kwargs)

    def select(self):
        super().select()
        self.redraw()

    def unselect(self):
        super().unselect()
        self.redraw()

    def redraw(self):
        if self.obj_1.layer is not None:
            self.move_to_layer(self.obj_1.layer)
        elif self.obj_2.layer is not None:
            self.move_to_layer(self.obj_2.layer)

        super().redraw()
        if self.texture:
            self.texture.invalidate()

    async def draw(self, update_state=True, **kwargs):
        if self.obj_1 is None or self.obj_2 is None:
            return
        prev_rotation = kwargs.get("rotation", self.rotation)

        p1 = self.obj_1.port_center(BaseElement.PORT_OUT, self.port_1)
        p2 = self.obj_2.port_center(BaseElement.PORT_IN, self.port_2)

        if self.dsp_connect is True:
            width = 2.5 * self.LINE_WIDTH
        else:
            width = 1.5 * self.LINE_WIDTH
        height = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
        theta = math.atan2(p1[0] - p2[0], p2[1] - p1[1])
        rotation = theta * 180.0 / math.pi
        position_x = p1[0] - math.cos(theta) * width / 2.0
        position_y = p1[1] - math.sin(theta) * width / 2.0

        await self.move(position_x, position_y, update_state=update_state, **kwargs)

        if update_state and abs(prev_rotation-rotation) > BaseElement.TINY_DELTA:
            await self.dispatch(
                self.action(
                    self.SET_ROTATION,
                    value=rotation,
                ),
                previous=dict(rotation=prev_rotation)
            )
        else:
            self.rotation = rotation

        self.group.set_position(self.position_x, self.position_y)
        self.group.set_rotation(Clutter.RotateAxis.Z_AXIS, self.rotation, 0, 0, 0)

        await self.set_size(
            math.ceil(width), math.ceil(height),
            update_state=update_state,
            **kwargs
        )
        if self.texture:
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

    async def set_size(self, width, height, **kwargs):
        await super().set_size(width, height, **kwargs)
        if self.texture:
            self.texture.set_size(width, height)
            self.texture.invalidate()

    async def move(self, x, y, **kwargs):
        await super().move(x, y, **kwargs)
        self.group.set_position(x, y)

