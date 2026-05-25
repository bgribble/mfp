#! /usr/bin/env python
'''
processor_element.py

A patch element corresponding to a signal or control processor
'''

from abc import ABCMeta, abstractmethod
import re

from flopsy import saga, mutates

from mfp import log
from .text_widget import TextWidget
from .modes.label_edit import LabelEditMode
from ..gui_main import MFPGUI
from .backend_interfaces import BackendInterface
from .base_element import BaseElement
from .param_info import ParamInfo


class ProcessorElementImpl(BackendInterface, metaclass=ABCMeta):
    @abstractmethod
    def redraw(self):
        pass


class ProcessorElement (BaseElement):
    help_patch = "processor.help.mfp"
    display_type = "processor"
    proc_type = None

    extra_params = {
        'show_label': ParamInfo(label="Show label", param_type=bool, show=True),
        'export_x': ParamInfo(label="Exported interface X", param_type=float),
        'export_y': ParamInfo(label="Exported interface Y", param_type=float),
        'export_w': ParamInfo(label="Exported interface width", param_type=float),
        'export_h': ParamInfo(label="Exported interface height", param_type=float),
        'panel_mode': ParamInfo(label="Panel mode", param_type=bool),
    }
    store_attrs = {
        **BaseElement.store_attrs, **extra_params
    }

    # constants
    label_off_x = 3
    label_off_y = 0

    def __init__(self, window, x, y, params=None):
        if params is None:
            params = {}

        super().__init__(window, x, y)

        self.show_label = params.get("show_label", True)
        self.panel_mode = params.get("panel_mode", False)

        # display elements
        self.label = TextWidget.get_backend(MFPGUI().backend_name)(self)
        self.label.set_position(self.label_off_x, self.label_off_y)
        self.label.set_color(self.get_color('text-color'))
        self.label.set_font_name(self.get_fontspec())
        self.label.signal_listen('text-changed', self.label_changed_cb)
        self.label.set_reactive(False)
        self.label_text = None

        if not self.show_label and self.children:
            self.label.hide()

        self.export_x = None
        self.export_y = None
        self.export_w = None
        self.export_h = None
        self.export_created = False

        self.obj_state = self.OBJ_HALFCREATED

    @classmethod
    def get_backend(cls, backend_name):
        return ProcessorElementImpl.get_backend(backend_name)

    def get_label(self):
        return self.label

    async def label_edit_start(self):
        self.obj_state = self.OBJ_HALFCREATED
        if not self.show_label:
            self.label.show()
        if self.obj_type:
            self.set_label_text(markup=False)
        await self.update()

    @saga('obj_type', 'obj_args', 'code')
    async def recreate_element(self, action, state_diff, previous):
        # don't recreate if this is the initial creation
        if "code" not in state_diff:
            if "obj_state" in state_diff and state_diff['obj_state'][0] is None:
                return
            if "obj_id" in state_diff and state_diff['obj_id'][0] is None:
                return

        if self.obj_type:
            args = f" {self.obj_args}" if self.obj_args is not None else ''
            yield await self.label_edit_finish(
                None, f"{self.obj_type}{args}"
            )

    @saga('show_label')
    async def change_label_offset(self, action, state_diff, previous):
        if "show_label" not in state_diff:
            return
        for child in self.children:
            if self.show_label:
                child.export_offset_y += 18
                await child.move(child.position_x, child.position_y + 18)
            else:
                child.export_offset_y -= 18
                await child.move(child.position_x, child.position_y - 18)

    async def label_edit_finish(self, widget, text=None, aborted=False):
        if text is not None and not aborted:
            obj_type = None
            obj_args = None
            # special form to eval for processor name
            if text[0] == "{":
                matches = re.search(
                    "^({.*})( (.*))?$", text
                )
                if matches:
                    obj_type = matches.group(1)
                    obj_args = matches.group(3)

            if not obj_type:
                parts = text.split(' ', 1)
                obj_type = parts[0]
                if len(parts) > 1:
                    obj_args = parts[1]
                else:
                    obj_args = None

            await self.create(obj_type, obj_args)

            self.set_label_text()

        if self.obj_id is not None and self.obj_state != self.OBJ_COMPLETE:
            self.obj_state = self.OBJ_COMPLETE

        if not self.show_label and self.children:
            self.label.hide()

        await self.update()

    async def make_edit_mode(self):
        return LabelEditMode(self.app_window, self, self.label)

    def set_label_text(self, markup=True):
        type_color = self.get_color("text-color:emph")
        if self.obj_args is None:
            if markup:
                self.label.set_markup(
                    f"<div class='tt color-{type_color}'>{self.obj_type}</div>"
                )
            else:
                self.label.set_text(f"{self.obj_type}")
        else:
            if markup:
                self.label.set_markup(
                    f"<div class='tt'><div class='color-{type_color}'>{self.obj_type}</div> {self.obj_args}</div>"
                )
            else:
                self.label.set_text(f"{self.obj_type} {self.obj_args}")

    @mutates('panel_mode')
    async def configure(self, params):
        need_update = False

        labelheight = 20
        if "show_label" in params:
            oldval = self.show_label
            self.show_label = params.get("show_label")
            if oldval ^ self.show_label:
                need_update = True
                if self.show_label or not self.children:
                    self.label.show()
                else:
                    self.label.hide()

        self.set_label_text()

        self.export_x = params.get("export_x")
        self.export_y = params.get("export_y")
        self.export_w = params.get("export_w")
        self.export_h = params.get("export_h")

        self.panel_mode = params.get("panel_mode", False)

        if self.export_x is not None and self.export_y is not None:
            self.panel_mode = True
            self.export_created = True

        params["width"] = max(self.width, params.get("export_w") or 0)
        params["height"] = max(self.height, (params.get("export_h") or 0) + labelheight)

        await super().configure(params)

        if self.obj_id is not None and self.obj_state != self.OBJ_COMPLETE:
            self.obj_state = self.OBJ_COMPLETE
            if self.export_created:
                await MFPGUI().mfp.create_export_gui(self.obj_id)
                need_update = True

        if "debug" in params:
            need_update = True

        if need_update:
            await self.update()
