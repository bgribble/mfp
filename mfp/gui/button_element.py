#! /usr/bin/env python
'''
button_element.py
A patch element corresponding to a "bang" or "toggle" style button

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from abc import ABCMeta, abstractmethod
from flopsy import saga

from mfp import log
from mfp.utils import catchall
from .text_widget import TextWidget
from .backend_interfaces import BackendInterface
from .base_element import BaseElement
from .modes.clickable import ClickableControlMode
from .modes.label_edit import LabelEditMode
from .param_info import ParamInfo, PyLiteral
from ..gui_main import MFPGUI
from ..bang import Bang


class ButtonElementImpl(BackendInterface, metaclass=ABCMeta):
    @abstractmethod
    def redraw(self):
        pass


class BangButtonElementImpl(BackendInterface, metaclass=ABCMeta):
    pass


class ToggleButtonElementImpl(BackendInterface, metaclass=ABCMeta):
    pass


class ToggleIndicatorElementImpl(BackendInterface, metaclass=ABCMeta):
    pass


class ButtonElement (BaseElement):
    proc_type = "var"
    help_patch = "button.help.mfp"
    style_defaults = {
        'porthole-height': 3,
        'porthole-width': 6,
        'porthole-minspace': 8,
        'porthole-border': 2,
        'padding': dict(top=0, bottom=0, left=0, right=0),
    }
    extra_params = {
        'label_text': ParamInfo(label="Button label", param_type=str, show=True),
    }
    store_attrs = {
        **BaseElement.store_attrs, **extra_params
    }

    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        self.indicator = False
        self.message = None

        padding = self.get_style('padding') or {}
        self.label = TextWidget.build(self)
        self.label.set_color(self.get_color('text-color'))
        self.label.set_font_name(self.get_fontspec())
        self.label.signal_listen('text-changed', self.label_changed_cb)
        self.label.set_reactive(False)
        self.label.set_position(padding.get('left', 0), padding.get('top', 0))

        self.label_text = ''
        self.param_list.append('label_text')

        # request update when value changes
        self.update_required = True

    @classmethod
    def get_backend(cls, backend_name):
        return ButtonElementImpl.get_backend(backend_name)

    async def center_label(self):
        label_halfwidth = self.label.get_property('width')/2.0
        label_halfheight = self.label.get_property('height')/2.0

        padding = self.get_style('padding') or {}
        nwidth = self.width
        nheight = self.height

        if label_halfwidth > 1:
            nwidth = max(self.width, 2*label_halfwidth + padding.get('left', 0) + padding.get('right', 0))
            nheight = max(self.height, 2*label_halfheight + padding.get('top', 0) + padding.get('bottom', 0))
            if nwidth != self.width or nheight != self.height:
                await self.set_size(nwidth, nheight)

        if nwidth and nheight:
            self.label.set_position(
                nwidth/2.0-label_halfwidth,
                nheight/2.0-label_halfheight-2
            )

    @saga("label_text")
    async def label_text_changed(self, action, state_diff, previous):
        self.label.set_markup(self.label_text, notify=True)
        yield None

    @catchall
    async def label_changed_cb(self, *args):
        await self.center_label()

    async def label_edit_start(self):
        return self.label_text

    async def label_edit_finish(self, widget, new_text, aborted=False):
        if not aborted:
            self.label_text = new_text
            self.send_params()
            if self.indicator and self.label_text:
                self.label.set_markup("<b>%s</b>" % self.label_text)
            else:
                self.label.set_markup(self.label_text or '')

            await self.center_label()
        self.redraw()

    async def configure(self, params):
        set_text = False

        if "value" in params:
            self.message = params.get("value")
            set_text = True

        if "label_text" in params:
            self.label_text = params.get("label_text", '')
            set_text = True

        if set_text:
            if self.indicator and self.label_text:
                self.label.set_markup("<b>%s</b>" % (self.label_text or ''))
            else:
                self.label.set_markup(self.label_text or '')
            await self.center_label()

        await super().configure(params)
        self.redraw()

    def select(self):
        BaseElement.select(self)
        self.redraw()

    def unselect(self):
        BaseElement.unselect(self)
        self.redraw()

    @saga('style')
    async def update_all_styles(self, action, state_diff, previous):
        self._all_styles = self.combine_styles()
        self.label.set_color(self.get_color('text-color'))
        yield None

    async def make_edit_mode(self):
        if self.obj_id is None:
            # create object
            await self.create(self.proc_type, str(self.indicator))

            # complete drawing
            if self.obj_id is None:
                return None
            self.draw_ports()
        self.redraw()

        return LabelEditMode(self.app_window, self, self.label)

    def make_control_mode(self):
        return ClickableControlMode(self.app_window, self, "Button control")


class BangButtonElement (ButtonElement):
    display_type = "button"

    extra_params = {
        'message': ParamInfo(label="Message on click", param_type=str, show=True),
    }
    store_attrs = {
        **ButtonElement.store_attrs,
        **extra_params
    }

    def __init__(self, window, x, y):
        super().__init__(window, x, y)
        self.message = Bang

    @classmethod
    def get_backend(cls, backend_name):
        return BangButtonElementImpl.get_backend(backend_name)

    async def clicked(self):
        if self.obj_id is not None:
            if self.message is Bang:
                MFPGUI().async_task(MFPGUI().mfp.send_bang(self.obj_id, 0))
            else:
                MFPGUI().async_task(MFPGUI().mfp.send(self.obj_id, 0, self.message))
        self.indicator = True
        self.redraw()

        return False

    def unclicked(self):
        self.indicator = False
        self.redraw()

        return False

    async def configure(self, params):
        if "message" in params:
            self.message = params.get("message")

        await super().configure(params)


class ToggleButtonElement (ButtonElement):
    display_type = "toggle"

    extra_params = {
        'on_message': ParamInfo(label="Message on enable", param_type=PyLiteral, show=True),
        'off_message': ParamInfo(label="Message on disable", param_type=PyLiteral, show=True),
    }
    store_attrs = {
        **ButtonElement.store_attrs,
        **extra_params
    }

    def __init__(self, window, x, y):
        super().__init__(window, x, y)
        self.off_message = False
        self.on_message = True

    @classmethod
    def get_backend(cls, backend_name):
        return ToggleButtonElementImpl.get_backend(backend_name)

    async def clicked(self, *args):
        message = None
        if self.indicator:
            message = self.off_message
            self.indicator = False
        else:
            message = self.on_message
            self.indicator = True

        if self.obj_id is not None:
            MFPGUI().async_task(MFPGUI().mfp.send(self.obj_id, 0, message))
        self.redraw()
        return False

    async def configure(self, params):
        await super().configure(params)

        if "on_message" in params:
            self.on_message = params.get("on_message")
        if "off_message" in params:
            self.off_message = params.get("off_message")
        if "message" in params:
            self.indicator = self.message == self.on_message

    async def create(self, init_type, init_args):
        await super().create(init_type, init_args)
        if self.obj_id:
            await MFPGUI().mfp.set_do_onload(self.obj_id, True)

    def unclicked(self):
        return False


class ToggleIndicatorElement (ButtonElement):
    display_type = "indicator"

    @classmethod
    def get_backend(cls, backend_name):
        return ToggleIndicatorElementImpl.get_backend(backend_name)

    def make_control_mode(self):
        return BaseElement.make_control_mode(self)

    def select(self, *args):
        super().select()
        self.draw_ports()
        self.redraw()

    def unselect(self, *args):
        super().unselect()
        self.hide_ports()
        self.redraw()

    def draw_ports(self):
        if self.selected:
            super().draw_ports()
