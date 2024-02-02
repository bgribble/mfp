#! /usr/bin/env python
'''
via_element.py
A patch element corresponding to a send or receive box

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

from abc import ABC, abstractmethod
from mfp.gui_main import MFPGUI
from .text_widget import TextWidget
from .base_element import BaseElement
from .modes.label_edit import LabelEditMode

from .backend_interfaces import BackendInterface


class ViaElement (BaseElement):
    display_type = None
    proc_type = None

    style_defaults = {
        'porthole_width': 0,
        'porthole_height': 0,
        'autoplace-dx': -2.5
    }

    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        self.param_list.append("label_text")
        self.connections_out = []
        self.connections_in = []

        self.label_text = None
        self.label = TextWidget.build(self)
        self.label.set_position(0, self.LABEL_Y)

        # configure label
        self.label.set_color(self.get_color('text-color'))
        self.label.set_font_name(self.get_fontspec())
        self.label.signal_listen('text-changed', self.text_changed_cb)
        
        self.width = self.VIA_SIZE + 2 * self.VIA_FUDGE
        self.height = self.VIA_SIZE + self.LABEL_HEIGHT + self.LABEL_FUDGE + 2 * self.VIA_FUDGE

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

    async def label_edit_start(self, *args):
        pass

    async def label_edit_finish(self, *args):
        # called by labeleditmode
        t = self.label.get_text()
        self.label_text = t
        if self.obj_id is None:
            await self.create_obj(t)
        self.recenter_label()

    async def configure(self, params):
        self.label_text = params.get("label_text", "")
        self.label.set_text(self.label_text)
        self.recenter_label()
        await super().configure(params)

    def port_position(self, port_dir, port_num):
        # vias connect to the center of the texture
        return ((self.VIA_SIZE + self.VIA_FUDGE) / 2.0,
                self.TEXTURE_Y + (self.VIA_SIZE + self.VIA_FUDGE) / 2.0)

    def select(self):
        BaseElement.select(self)
        self.label.set_color(self.get_color('text-color'))
        self.redraw()

    def unselect(self):
        BaseElement.unselect(self)
        self.label.set_color(self.get_color('text-color'))
        self.redraw()

    async def make_edit_mode(self):
        return LabelEditMode(self.app_window, self, self.label)

class SendViaElementImpl(ABC, BackendInterface):
    @abstractmethod
    def redraw(self):
        pass


class SendViaElement (ViaElement):
    display_type = "sendvia"
    proc_type = "send"

    @classmethod
    def get_factory(cls):
        return SendViaElementImpl.get_backend(MFPGUI().appwin.backend_name)

    async def label_edit_finish(self, *args):
        await ViaElement.label_edit_finish(self, *args)
        await MFPGUI().mfp.send(self.obj_id, 1, self.parse_label(self.label.get_text()))


class SendSignalViaElementImpl(ABC, BackendInterface):
    @abstractmethod
    def redraw(self):
        pass


class SendSignalViaElement (SendViaElement):
    display_type = "sendsignalvia"
    proc_type = "send~"

    @classmethod
    def get_factory(cls):
        return SendSignalViaElementImpl.get_backend(MFPGUI().appwin.backend_name)


class ReceiveViaElementImpl(ABC, BackendInterface):
    @abstractmethod
    def redraw(self):
        pass


class ReceiveViaElement (ViaElement):
    display_type = "recvvia"
    proc_type = "recv"

    async def label_edit_finish(self, *args):
        await ViaElement.label_edit_finish(self, *args)
        await MFPGUI().mfp.send(self.obj_id, 1, self.parse_label(self.label.get_text()))

    @classmethod
    def get_factory(cls):
        return ReceiveViaElementImpl.get_backend(MFPGUI().appwin.backend_name)


class ReceiveSignalViaElementImpl(ABC, BackendInterface):
    @abstractmethod
    def redraw(self):
        pass


class ReceiveSignalViaElement (ReceiveViaElement):
    display_type = "recvsignalvia"
    proc_type = "recv~"

    @classmethod
    def get_factory(cls):
        return ReceiveSignalViaElementImpl.get_backend(MFPGUI().appwin.backend_name)
