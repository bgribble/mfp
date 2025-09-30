#! /usr/bin/env python
'''
via_element.py
A patch element corresponding to a send or receive box

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

from abc import ABCMeta, abstractmethod
from flopsy import saga
from mfp.gui_main import MFPGUI
from .text_widget import TextWidget
from .base_element import BaseElement
from .modes.label_edit import LabelEditMode

from .backend_interfaces import BackendInterface


class ViaElement (BaseElement):
    display_type = None
    proc_type = None
    help_patch = "via.help.mfp"

    style_defaults = {
        'porthole-width': 0,
        'porthole-height': 0,
        'autoplace-dx': -2.5
    }

    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        self.param_list.append("label_text")
        self.connections_out = []
        self.connections_in = []

        self.label_text_set = False
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
        self.recenter_label(*args)

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

    @saga('obj_type', 'obj_args')
    async def recreate_element(self, action, state_diff, previous):
        if "obj_state" in state_diff and state_diff['obj_state'][0] is None:
            return

        if self.obj_type:
            args = f" {self.obj_args}" if self.obj_args is not None else ''
            yield await self.label_edit_finish(
                None, f"{self.obj_type}{args}"
            )

    @saga('style')
    async def update_all_styles(self, action, state_diff, previous):
        self._all_styles = self.combine_styles()
        self.label.set_color(self.get_color('text-color'))
        yield None

    async def label_edit_start(self, *args):
        pass

    async def label_edit_finish(self, widget=None, text=None, aborted=False):
        # called by labeleditmode
        t = self.label.get_text()
        if not aborted:
            self.label_text = t
            if self.obj_id is None:
                await self.create_obj(t)
            self.recenter_label()
            await MFPGUI().mfp.send(self.obj_id, 1, self.parse_label(self.label.get_text()))

    async def configure(self, params):
        self.label_text = params.get("label_text", "")

        # don't call the recenter callback on initial setup
        self.label.set_text(self.label_text, notify=self.label_text_set)

        if "position_x" not in params:
            self.recenter_label()
        await super().configure(params)
        self.label_text_set = True

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


class SendViaElementImpl(metaclass=ABCMeta):
    @abstractmethod
    def redraw(self):
        pass


class SendViaElement (BackendInterface, ViaElement):
    display_type = "sendvia"
    proc_type = "send"


class SendSignalViaElementImpl(metaclass=ABCMeta):
    @abstractmethod
    def redraw(self):
        pass


class SendSignalViaElement (BackendInterface, ViaElement):
    display_type = "sendsignalvia"
    proc_type = "send~"


class ReceiveViaElementImpl(metaclass=ABCMeta):
    @abstractmethod
    def redraw(self):
        pass


class ReceiveViaElement (BackendInterface, ViaElement):
    display_type = "recvvia"
    proc_type = "recv"


class ReceiveSignalViaElementImpl(metaclass=ABCMeta):
    @abstractmethod
    def redraw(self):
        pass


class ReceiveSignalViaElement (BackendInterface, ViaElement):
    display_type = "recvsignalvia"
    proc_type = "recv~"
