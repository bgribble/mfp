#! /usr/bin/env python
'''
enum_element.py
A patch element corresponding to a number box or enum selector

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from abc import ABCMeta, abstractmethod
from flopsy import saga, mutates

from mfp.gui_main import MFPGUI
from .backend_interfaces import BackendInterface
from .text_widget import TextWidget
from .base_element import BaseElement
from .modes.enum_control import EnumEditMode, EnumControlMode

from .param_info import ParamInfo, ListOfPairs


class EnumElementImpl(BackendInterface, metaclass=ABCMeta):
    @abstractmethod
    def redraw(self):
        pass


class EnumElement (BaseElement):
    display_type = "enum"
    proc_type = "enum"
    help_patch = "number.help.mfp"
    store_attrs = {
        **BaseElement.store_attrs,
        **{
            'digits': ParamInfo(label="Digits", param_type=int, show=True),
            'min_value': ParamInfo(label="Min value", param_type=float, show=True, null=True),
            'max_value': ParamInfo(label="Max value", param_type=float, show=True, null=True),
            'scientific': ParamInfo(label="Use scientific notation", param_type=bool, show=True),
        }
    }
    PORT_TWEAK = 7

    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        self.value = 0
        self.digits = 1
        self.min_value = None
        self.max_value = None
        self.scientific = False
        self.format_str = "%.1f"

        self.connections_out = []
        self.connections_in = []
        self.update_required = True

        self.obj_state = self.OBJ_HALFCREATED

        # configure label
        self.label = TextWidget.build(self)
        self.label.set_position(4, 1)
        self.label.set_font_name(self.get_fontspec())
        self.label.set_color(self.get_color('text-color'))
        self.label.signal_listen('text-changed', self.text_changed_cb)
        self.label.set_text(self.format_value(self.value))

    @classmethod
    def get_backend(cls, backend_name):
        return EnumElementImpl.get_backend(backend_name)

    @saga('obj_type', 'obj_args')
    async def recreate_element(self, action, state_diff, previous):
        if "obj_state" in state_diff and state_diff['obj_state'][0] is None:
            return

        if self.obj_type:
            args = f" {self.obj_args}" if self.obj_args is not None else ''
            yield await self.label_edit_finish(
                None, f"{self.obj_type}{args}"
            )

    @saga('min_value', 'max_value', 'digits', 'scientific')
    async def reformat_label(self, action, state_diff, previous):
        self.format_update()
        yield await self.update_value(self.value)

    def format_update(self):
        if self.scientific:
            oper = "e"
        else:
            oper = "f"
        self.format_str = "%%.%d%s" % (self.digits, oper)

    def format_value(self, value):
        if self.min_value is not None and value < self.min_value:
            value = self.min_value
        if self.max_value is not None and value > self.max_value:
            value = self.max_value
        return self.format_str % value

    async def text_changed_cb(self, *args):
        lwidth = self.label.get_property('width')
        bwidth = self.width

        new_w = None
        if lwidth > (bwidth - 20):
            new_w = lwidth + 20
        elif (bwidth > 35) and (lwidth < (bwidth - 20)):
            new_w = max(35, lwidth + 20)

        if new_w is not None:
            await self.set_size(new_w, self.height)

    async def create_obj(self):
        if self.obj_id is None:
            await self.create(self.proc_type, str(self.value))
        if self.obj_id is None:
            print("EnumElement: could not create var obj")
        else:
            await MFPGUI().mfp.set_do_onload(self.obj_id, True)
            self.obj_state = self.OBJ_COMPLETE

        self.draw_ports()
        self.redraw()

    @mutates('min_value', 'max_value')
    async def set_bounds(self, lower, upper):
        self.min_value = lower
        self.max_value = upper

        if ((self.value < self.min_value) or (self.value > self.max_value)):
            await self.update_value(self.value)
        self.send_params()

    async def update_value(self, value):
        if self.min_value is not None and value < self.min_value:
            value = self.min_value

        if self.max_value is not None and value > self.max_value:
            value = self.max_value

        # called by enumcontrolmode
        str_rep = self.format_value(value)
        self.label.set_text(str_rep)
        self.value = float(str_rep)

        if self.obj_id is None:
            await self.create_obj()
        if self.obj_id is not None:
            await MFPGUI().mfp.send(self.obj_id, 0, self.value)

    async def update(self):
        self.label.set_text(self.format_value(self.value))
        self.redraw()

    async def label_edit_start(self):
        pass

    async def label_edit_finish(self, *args):
        # called by labeleditmode
        t = self.label.get_text()
        await self.update_value(float(t))
        if self.obj_id is None:
            await self.create_obj()
        await MFPGUI().mfp.send(self.obj_id, 0, self.value)
        self.redraw()

    async def configure(self, params):
        fmt_changed = False
        val_changed = False

        v = params.get("value", float(self.obj_args or 0.0))
        if v != self.value:
            self.value = v
            val_changed = True

        v = params.get("scientific")
        if v:
            if not self.scientific:
                fmt_changed = True
            self.scientific = True
        else:
            if self.scientific:
                fmt_changed = True
            self.scientific = False

        v = params.get("digits")
        if v is not None and v != self.digits:
            self.digits = v
            fmt_changed = True

        if fmt_changed:
            self.format_update()
        if fmt_changed or val_changed:
            self.label.set_text(self.format_value(self.value))

        if 'width' in params:
            del params['width']
        if 'height' in params:
            del params['height']

        await super().configure(params)
        self.redraw()

    def select(self):
        BaseElement.select(self)
        self.label.set_color(self.get_color('text-color'))
        self.redraw()

    def unselect(self):
        BaseElement.unselect(self)
        self.label.set_color(self.get_color('text-color'))
        self.redraw()

    async def make_edit_mode(self):
        return EnumEditMode(self.app_window, self, self.label)

    def make_control_mode(self):
        return EnumControlMode(self.app_window, self)
