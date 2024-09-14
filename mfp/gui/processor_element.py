#! /usr/bin/env python
'''
processor_element.py

A patch element corresponding to a signal or control processor
'''

from abc import ABCMeta, abstractmethod

from flopsy import saga

from mfp import log
from .text_widget import TextWidget
from .modes.label_edit import LabelEditMode
from ..gui_main import MFPGUI
from .backend_interfaces import BackendInterface
from .base_element import BaseElement


class ProcessorElementImpl(BackendInterface, metaclass=ABCMeta):
    @abstractmethod
    def redraw(self):
        pass


class ProcessorElement (BaseElement):
    display_type = "processor"
    proc_type = None

    # constants
    label_off_x = 3
    label_off_y = 0

    def __init__(self, window, x, y, params=None):
        if params is None:
            params = {}

        super().__init__(window, x, y)

        self.param_list.extend([
            "show_label",
            "export_x",
            "export_y",
            "export_w",
            "export_h"
        ])
        self.show_label = params.get("show_label", True)

        # display elements
        self.label = TextWidget.get_backend(MFPGUI().backend_name)(self)
        self.label.set_position(self.label_off_x, self.label_off_y)
        self.label.set_color(self.get_color('text-color'))
        self.label.set_font_name(self.get_fontspec())
        self.label.signal_listen('text-changed', self.label_changed_cb)
        self.label.set_reactive(False)
        self.label_text = None

        if not self.show_label:
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
        await self.update()

    @saga('obj_type', 'obj_args')
    async def recreate_element(self, action, state_diff):
        if self.obj_type:
            yield await self.label_edit_finish(None, f"{self.obj_type} {self.obj_args}")

    async def label_edit_finish(self, widget, text=None):
        if text is not None:
            parts = text.split(' ', 1)
            obj_type = parts[0]
            if len(parts) > 1:
                obj_args = parts[1]
            else:
                obj_args = None

            await self.create(obj_type, obj_args)

            # obj_args may get forcibly changed on create
            if self.obj_args and (len(parts) < 2 or self.obj_args != parts[1]):
                self.label.set_text(self.obj_type + ' ' + self.obj_args)

        if self.obj_id is not None and self.obj_state != self.OBJ_COMPLETE:
            self.obj_state = self.OBJ_COMPLETE

        if not self.show_label:
            self.label.hide()

        await self.update()

    async def make_edit_mode(self):
        return LabelEditMode(self.app_window, self, self.label)

    async def configure(self, params):
        if self.obj_args is None:
            self.label.set_text("%s" % (self.obj_type,))
        else:
            self.label.set_text("%s %s" % (self.obj_type, self.obj_args))

        need_update = False

        labelheight = 20
        if "show_label" in params:
            oldval = self.show_label
            self.show_label = params.get("show_label")
            if oldval ^ self.show_label:
                need_update = True
                if self.show_label:
                    self.label.show()
                else:
                    self.label.hide()

        self.export_x = params.get("export_x")
        self.export_y = params.get("export_y")
        self.export_w = params.get("export_w")
        self.export_h = params.get("export_h")
        if self.export_x is not None and self.export_y is not None:
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
