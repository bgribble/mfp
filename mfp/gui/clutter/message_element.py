"""
clutter/message_element.py -- clutter backend for message elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from gi.repository import Clutter
import cairo

from mfp.utils import catchall
from ..colordb import ColorDB
from .base_element import ClutterBaseElementBackend
from ..base_element import BaseElement
from ..message_element import (
    MessageElement,
    MessageElementImpl,
    TransientMessageElement,
    TransientMessageElementImpl,
)


class ClutterMessageElementImpl(MessageElement, MessageElementImpl, ClutterBaseElementBackend):
    backend_name = "clutter"

    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        # create elements
        self.texture = Clutter.Canvas.new()
        self.texture.connect("draw", self.draw_cb)
        self.group.set_content(self.texture)
        self.group.set_reactive(True)

        # resize widget when text gets longer
        self.handler_id = self.label.signal_listen('text-changed', self.text_changed_cb)
        self.width = 35
        self.height = 25
        self.texture.set_size(self.width, self.height)
        self.group.set_size(self.width, self.height)
        self.group.set_position(x, y)
        self.redraw()

    async def delete(self, **kwargs):
        if self.texture:
            self.group.set_content(None)
            self.texture = None
        if self.label:
            self.label.signal_unlisten(self.handler_id)
            await self.label.delete()
            self.label = None

        await super().delete(**kwargs)

    def redraw(self):
        if not self.texture:
            return
        super().redraw()
        self.texture.invalidate()

    async def set_size(self, width, height):
        await super().set_size(width, height)
        self.texture.set_size(width, height)
        await self.update()

    async def text_changed_cb(self, *args):
        if self.group is None:
            return
        lwidth = self.label.get_property('width')
        bwidth = self.texture.get_property('width')

        new_w = None
        if lwidth > (bwidth - 20):
            new_w = lwidth + 20
        elif (bwidth > 35) and (lwidth < (bwidth - 20)):
            new_w = max(35, lwidth + 20)

        if new_w is not None:
            await self.set_size(new_w, self.texture.get_property('height'))
            await self.update()

    def draw_cb(self, texture, ct, width, height):
        if self.clickstate:
            lw = 5.0
        else:
            lw = 2.0

        w = width - lw
        h = height - lw
        c = None

        # clear the drawing area
        ct.save()
        ct.set_operator(cairo.OPERATOR_CLEAR)
        ct.paint()
        ct.restore()

        if self.obj_state == BaseElement.OBJ_COMPLETE:
            ct.set_dash([])
        else:
            ct.set_dash([8, 4])

        ct.set_line_width(lw)

        ct.set_antialias(cairo.ANTIALIAS_NONE)
        ct.translate(lw / 2.0, lw / 2.0)
        ct.move_to(0, 0)
        ct.line_to(0, h)
        ct.line_to(w, h)
        ct.curve_to(w - 8, h - 8, w - 8, 8, w, 0)
        ct.line_to(0, 0)
        ct.close_path()

        # fill to paint the background
        c = ColorDB().normalize(self.get_color('fill-color'))
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        ct.fill_preserve()

        # stroke to draw the outline
        c = ColorDB().normalize(self.get_color('stroke-color'))
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        ct.stroke()

        return True


class ClutterTransientMessageElementImpl(
    TransientMessageElement,
    TransientMessageElementImpl,
    ClutterMessageElementImpl,
):
    backend_name = "clutter"

