"""
clutter/via_element.py == Clutter implementation of via elements

send/receive, signal/control - 4 types total

Copyright (c) Bill Gribble <grib@billgribble.com>
"""
import math

from gi.repository import Clutter

from ..colordb import ColorDB
from .base_element import ClutterBaseElementImpl
from ..via_element import (
    SendViaElement,
    SendViaElementImpl,
    SendSignalViaElement,
    SendSignalViaElementImpl,
    ReceiveViaElement,
    ReceiveViaElementImpl,
    ReceiveSignalViaElement,
    ReceiveSignalViaElementImpl
)


class ClutterBaseViaElementImpl(ClutterBaseElementImpl):
    backend_name = "clutter"

    VIA_SIZE = 10
    VIA_FUDGE = 5
    LABEL_HEIGHT = 15
    LABEL_FUDGE = 0
    LABEL_Y = 0

    def __init__(self, window, x, y):
        self.label = None

        super().__init__(window, x, y)

        txs = self.VIA_SIZE + self.VIA_FUDGE
        self.texture = Clutter.CairoTexture.new(txs, txs)
        self.texture.set_size(txs, txs)
        self.group.set_size(txs, txs)
        self.texture.set_surface_size(txs, txs)

        self.texture.connect("draw", self.draw_cb)
        self.texture.set_position(0, self.TEXTURE_Y)

        self.group.set_reactive(True)
        self.group.add_actor(self.texture)
        self.group.set_position(x, y)

        self.recenter_label()
        self.redraw()

    def redraw(self):
        self.texture.invalidate()

    def recenter_label(self, *args):
        w = self.label.get_width()
        _, y = self.label.get_position()
        self.label.set_position((self.texture.get_width() - w) / 2.0, y)

    def port_position(self, port_dir, port_num):
        # vias connect to the center of the texture
        return ((self.VIA_SIZE + self.VIA_FUDGE) / 2.0,
                self.TEXTURE_Y + (self.VIA_SIZE + self.VIA_FUDGE) / 2.0)

    def draw_cb(self, texture, ct):
        self.texture.clear()

        if self.GLYPH_STYLE in ("empty_circled", "filled_circled"):
            arcsize = self.VIA_SIZE / 3.5
            linewidth = 1
        else:
            arcsize = self.VIA_SIZE / 2.0
            linewidth = 3

        # ct.translate(0.5, 0.5)
        ct.set_line_width(linewidth)
        cent = (self.VIA_SIZE + self.VIA_FUDGE) / 2.0
        ct.arc(cent, cent, arcsize, 0, 2 * math.pi)
        color = ColorDB().normalize(self.get_color('stroke-color'))
        if self.GLYPH_STYLE[:5] == "empty":
            ct.set_source_rgba(color.red, color.green, color.blue, color.alpha)
            ct.stroke()
        else:
            ct.set_source_rgba(color.red, color.green, color.blue, color.alpha)
            ct.fill()

        if self.GLYPH_STYLE[-7:] == "circled":
            ct.set_source_rgba(color.red, color.green, color.blue, color.alpha)
            ct.set_line_width(1)
            cent = (self.VIA_SIZE + self.VIA_FUDGE) / 2.0
            ct.arc(cent, cent, self.VIA_SIZE/2.0, 0, 2 * math.pi)
            ct.stroke()


class ClutterSendViaElementImpl(SendViaElementImpl, ClutterBaseViaElementImpl, SendViaElement):
    GLYPH_STYLE = "empty"
    LABEL_Y = ClutterBaseViaElementImpl.VIA_SIZE + ClutterBaseViaElementImpl.VIA_FUDGE / 2.0
    TEXTURE_Y = 0

    def redraw(self):
        ClutterBaseViaElementImpl.redraw(self)


class ClutterSendSignalViaElementImpl(
    SendSignalViaElementImpl, ClutterBaseViaElementImpl, SendSignalViaElement
):
    VIA_SIZE = 12
    GLYPH_STYLE = "empty_circled"
    LABEL_Y = ClutterBaseViaElementImpl.VIA_SIZE + ClutterBaseViaElementImpl.VIA_FUDGE / 2.0
    TEXTURE_Y = 0

    def redraw(self):
        ClutterBaseViaElementImpl.redraw(self)


class ClutterReceiveViaElementImpl(ReceiveViaElementImpl, ClutterBaseViaElementImpl, ReceiveViaElement):
    GLYPH_STYLE = "filled"
    LABEL_Y = 0
    LABEL_FUDGE = 2.5
    TEXTURE_Y = ClutterBaseViaElementImpl.LABEL_HEIGHT + LABEL_FUDGE

    def redraw(self):
        ClutterBaseViaElementImpl.redraw(self)


class ClutterReceiveSignalViaElementImpl(
    ReceiveSignalViaElementImpl, ClutterBaseViaElementImpl, ReceiveSignalViaElement
):
    VIA_SIZE = 12
    GLYPH_STYLE = "filled_circled"
    LABEL_Y = 0
    LABEL_FUDGE = 2.5
    TEXTURE_Y = ClutterBaseViaElementImpl.LABEL_HEIGHT + LABEL_FUDGE

    def redraw(self):
        ClutterBaseViaElementImpl.redraw(self)
