#! /usr/bin/env python2.6
'''
via_element.py
A patch element corresponding to a send or receive box

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter
import math
from patch_element import PatchElement
from mfp import MFPGUI
from .modes.label_edit import LabelEditMode
from .modes.enum_control import EnumControlMode


class ViaElement (PatchElement):
    display_type = None
    proc_type = None
    porthole_width = 0
    porthole_height = 0
    autoplace_dx = -2.5

    VIA_SIZE = 10
    VIA_FUDGE = 5
    LABEL_HEIGHT = 15
    LABEL_FUDGE = 0
    LABEL_Y = 0
    STYLE = None

    def __init__(self, window, x, y):
        PatchElement.__init__(self, window, x, y)

        self.connections_out = []
        self.connections_in = []
        self.editable = False

        # create elements
        txs = self.VIA_SIZE + self.VIA_FUDGE
        self.texture = Clutter.CairoTexture.new(txs, txs)
        self.texture.set_size(txs, txs)
        self.texture.set_surface_size(txs, txs)

        self.texture.connect("draw", self.draw_cb)
        self.texture.set_position(0, self.TEXTURE_Y)
        self.label = Clutter.Text()
        self.label.set_position(0, self.LABEL_Y)
        self.set_reactive(True)
        self.add_actor(self.texture)
        self.add_actor(self.label)

        # configure label
        self.label.set_color(window.color_unselected)
        self.label.connect('text-changed', self.text_changed_cb)

        self.move(x, y)
        self.set_size(self.VIA_SIZE + 2 * self.VIA_FUDGE,
                      self.VIA_SIZE + self.LABEL_HEIGHT + self.LABEL_FUDGE + 2 * self.VIA_FUDGE)

        self.recenter_label()
        self.texture.invalidate()

    def draw_cb(self, texture, ct):
        self.texture.clear()
        if self.selected:
            color = self.stage.color_selected
        else:
            color = self.stage.color_unselected

        ct.set_source_rgba(color.red, color.green, color.blue, 1.0)

        # ct.translate(0.5, 0.5)
        ct.set_line_width(3)
        cent = (self.VIA_SIZE + self.VIA_FUDGE) / 2.0
        ct.arc(cent, cent, self.VIA_SIZE / 2.0, 0, 2 * math.pi)
        if self.STYLE == "empty":
            ct.stroke()
        else:
            ct.fill()

    def recenter_label(self):
        w = self.label.get_width()
        x, y = self.label.get_position()
        self.label.set_position((self.texture.get_width() - self.label.get_width()) / 2.0, y)

    def text_changed_cb(self, *args):
        self.recenter_label()

    def create_obj(self, label_text):
        if self.obj_id is None:
            self.create(self.proc_type, '"%s"' % label_text)
        if self.obj_id is None:
            print "ViaElement: could not create via obj"

        self.send_params()

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

    def label_edit_finish(self, *args):
        # called by labeleditmode
        t = self.label.get_text()
        if self.obj_id is None:
            self.create_obj(t)
        self.recenter_label()

    def configure(self, params):
        self.label.set_text(params.get("label", ""))
        self.recenter_label()
        PatchElement.configure(self, params)

    def port_position(self, port_dir, port_num):
        # vias connect to the center of the texture
        return ((self.VIA_SIZE + self.VIA_FUDGE) / 2.0,
                self.TEXTURE_Y + (self.VIA_SIZE + self.VIA_FUDGE) / 2.0)

    def select(self):
        self.selected = True
        self.texture.invalidate()

    def unselect(self):
        self.selected = False
        self.texture.invalidate()

    def delete(self):
        for c in self.connections_out + self.connections_in:
            c.delete()
        PatchElement.delete(self)

    def make_edit_mode(self):
        return LabelEditMode(self.stage, self, self.label)


class SendViaElement (ViaElement):
    STYLE = "empty"
    LABEL_Y = ViaElement.VIA_SIZE + ViaElement.VIA_FUDGE / 2.0
    TEXTURE_Y = 0

    display_type = "sendvia"
    proc_type = "send"


class ReceiveViaElement (ViaElement):
    STYLE = "filled"
    LABEL_Y = 0
    LABEL_FUDGE = 2.5
    TEXTURE_Y = ViaElement.LABEL_HEIGHT + LABEL_FUDGE

    display_type = "recvvia"
    proc_type = "recv"
