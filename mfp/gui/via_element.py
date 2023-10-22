#! /usr/bin/env python
'''
via_element.py
A patch element corresponding to a send or receive box

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter
import math
from mfp.gui_main import MFPGUI
from .text_widget import TextWidget
from .patch_element import PatchElement
from .modes.label_edit import LabelEditMode
from .colordb import ColorDB


class ViaElement (PatchElement):
    display_type = None
    proc_type = None

    style_defaults = {
        'porthole_width': 0,
        'porthole_height': 0,
        'autoplace-dx': -2.5
    }

    VIA_SIZE = 10
    VIA_FUDGE = 5
    LABEL_HEIGHT = 15
    LABEL_FUDGE = 0
    LABEL_Y = 0
    GLYPH_STYLE = None

    def __init__(self, window, x, y):
        PatchElement.__init__(self, window, x, y)
        self.param_list.append("label_text")
        self.connections_out = []
        self.connections_in = []

        # create elements
        txs = self.VIA_SIZE + self.VIA_FUDGE
        self.texture = Clutter.CairoTexture.new(txs, txs)
        self.texture.set_size(txs, txs)
        self.texture.set_surface_size(txs, txs)

        self.texture.connect("draw", self.draw_cb)
        self.texture.set_position(0, self.TEXTURE_Y)
        self.label_text = None
        self.label = TextWidget(self)
        self.label.set_position(0, self.LABEL_Y)
        self.set_reactive(True)
        self.add_actor(self.texture)

        # configure label
        self.label.set_color(self.get_color('text-color'))
        self.label.set_font_name(self.get_fontspec())
        self.label.signal_listen('text-changed', self.text_changed_cb)

        self.move(x, y)
        self.set_size(self.VIA_SIZE + 2 * self.VIA_FUDGE,
                      self.VIA_SIZE + self.LABEL_HEIGHT + self.LABEL_FUDGE + 2 * self.VIA_FUDGE)

        self.recenter_label()
        self.texture.invalidate()

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
        color = ColorDB.to_cairo(self.get_color('stroke-color'))
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

    def recenter_label(self):
        w = self.label.get_width()
        x, y = self.label.get_position()
        self.label.set_position((self.texture.get_width() - w) / 2.0, y)

    def text_changed_cb(self, *args):
        self.recenter_label()

    def parse_label(self, txt):
        parts = txt.split('/')
        port = 0
        name = txt
        if len(parts) == 2:
            try:
                port = int(parts[1])
                name = parts[0]
            except Exception:
                pass
        return (name, port)

    async def create_obj(self, label_text):
        if self.obj_id is None:
            (name, port) = self.parse_label(label_text)
            await self.create(self.proc_type, '"%s",%s' % (name, port))

    def move(self, x, y):
        self.position_x = x
        self.position_y = y
        self.set_position(x, y)

        for c in self.connections_out:
            c.draw()

        for c in self.connections_in:
            c.draw()

    def label_edit_start(self):
        pass

    async def label_edit_finish(self, *args):
        # called by labeleditmode
        t = self.label.get_text()
        self.label_text = t
        if self.obj_id is None:
            await self.create_obj(t)
        self.recenter_label()

    def configure(self, params):
        self.label_text = params.get("label_text", "")
        self.label.set_text(self.label_text)
        self.recenter_label()
        PatchElement.configure(self, params)

    def port_position(self, port_dir, port_num):
        # vias connect to the center of the texture
        return ((self.VIA_SIZE + self.VIA_FUDGE) / 2.0,
                self.TEXTURE_Y + (self.VIA_SIZE + self.VIA_FUDGE) / 2.0)

    def select(self):
        PatchElement.select(self)
        self.label.set_color(self.get_color('text-color'))
        self.texture.invalidate()

    def unselect(self):
        PatchElement.unselect(self)
        self.label.set_color(self.get_color('text-color'))
        self.texture.invalidate()

    def make_edit_mode(self):
        return LabelEditMode(self.stage, self, self.label)


class SendViaElement (ViaElement):
    GLYPH_STYLE = "empty"
    LABEL_Y = ViaElement.VIA_SIZE + ViaElement.VIA_FUDGE / 2.0
    TEXTURE_Y = 0

    display_type = "sendvia"
    proc_type = "send"

    async def label_edit_finish(self, *args):
        await ViaElement.label_edit_finish(self, *args)
        await MFPGUI().mfp.send(self.obj_id, 1, self.parse_label(self.label.get_text()))


class SendSignalViaElement (SendViaElement):
    VIA_SIZE = 12
    GLYPH_STYLE = "empty_circled"
    display_type = "sendsignalvia"
    proc_type = "send~"


class ReceiveViaElement (ViaElement):
    GLYPH_STYLE = "filled"
    LABEL_Y = 0
    LABEL_FUDGE = 2.5
    TEXTURE_Y = ViaElement.LABEL_HEIGHT + LABEL_FUDGE

    display_type = "recvvia"
    proc_type = "recv"

    async def label_edit_finish(self, *args):
        await ViaElement.label_edit_finish(self, *args)
        await MFPGUI().mfp.send(self.obj_id, 1, self.parse_label(self.label.get_text()))


class ReceiveSignalViaElement (ReceiveViaElement):
    VIA_SIZE = 12
    GLYPH_STYLE = "filled_circled"
    display_type = "recvsignalvia"
    proc_type = "recv~"
