#! /usr/bin/env python
'''
text_element.py
A text element (comment) in a patch
'''

from abc import ABCMeta, abstractmethod

from flopsy import saga
from mfp.gui_main import MFPGUI
from mfp import log
from .base_element import BaseElement
from .backend_interfaces import BackendInterface
from .colordb import ColorDB
from .modes.label_edit import LabelEditMode
from .modes.clickable import AltClickableControlMode
from .param_info import ParamInfo
from .text_widget import TextWidget


class TextElementImpl(BackendInterface, metaclass=ABCMeta):
    @abstractmethod
    def redraw(self):
        pass


class TextElement (BaseElement):
    display_type = "text"
    proc_type = "text"

    ELBOW_ROOM = 5

    extra_params = {
        'clickchange': ParamInfo(label="Click to change", param_type=bool, show=True),
        'max_width': ParamInfo(label="Max width", param_type=float, show=True),
        'value': ParamInfo(label="Text value", param_type=str, show=False),
        'default': ParamInfo(label="Default value", param_type=str, show=False),
    }

    store_attrs = {
        **BaseElement.store_attrs, **extra_params
    }

    style_defaults = {
        'border': False,
        'draw-ports': 'selected'
    }

    def __init__(self, window, x, y):
        super().__init__(window, x, y)
        self.value = ''
        self.clickchange = False
        self.default = ''
        self.max_width = 600

        self.param_list.extend([*self.extra_params])

        # these can't be initialized until there's a backend
        type(self).style_defaults.update({
            'fill-color': ColorDB().find('transparent'),
            'fill-color:selected': ColorDB().find('transparent'),
        })

        self.label = TextWidget.build(self)
        self.label.set_color(self.get_color('text-color'))
        self.label.set_font_name(self.get_fontspec())
        self.label.set_position(3, 3)

        self.label_changed_cb = self.label.signal_listen('text-changed', self.text_changed_cb)

    @classmethod
    def get_backend(cls, backend_name):
        return TextElementImpl.get_backend(backend_name)

    @saga('obj_type', 'obj_args')
    async def recreate_element(self, action, state_diff, previous):
        if "obj_state" in state_diff and state_diff['obj_state'][0] == None:
            return

        if self.obj_type:
            args = f" {self.obj_args}" if self.obj_args is not None else ''
            yield await self.label_edit_finish(
                None, f"{self.obj_type}{args}"
            )

    async def update(self):
        await self.set_size(
            self.label.get_width() + 2*self.ELBOW_ROOM,
            self.label.get_height() + self.ELBOW_ROOM
        )
        self.redraw()
        self.draw_ports()

    async def label_edit_start(self):
        return self.value

    async def label_edit_finish(self, widget, new_text, aborted=False):
        if self.obj_id is None:
            await self.create(self.proc_type, None)
        if self.obj_id is None:
            log.warning("TextElement: could not create obj")
        elif new_text != self.value and not aborted:
            self.value = new_text
            self.set_text()
            await MFPGUI().mfp.send(self.obj_id, 0, self.value)
        await self.update()

    async def end_edit(self):
        await BaseElement.end_edit(self)
        self.set_text()

    async def text_changed_cb(self, *args):
        await self.update()

    async def clicked(self):
        def newtext(txt):
            self.value = txt or ''
            self.set_text()
        if self.selected and self.clickchange:
            await self.app_window.cmd_get_input("New text:", newtext, self.value)
        return True

    def set_text(self):
        if len(self.value) > 0:
            self.label.set_markup(self.value)
        else:
            self.value = self.default or '...'
            self.label.set_markup(self.value)

    def unclicked(self):
        return True

    def select(self, *args):
        BaseElement.select(self)
        self.label.set_color(self.get_color('text-color'))
        self.redraw()
        self.draw_ports()

    def unselect(self, *args):
        BaseElement.unselect(self)
        self.label.set_color(self.get_color('text-color'))
        self.redraw()
        self.hide_ports()

    async def make_edit_mode(self):
        return LabelEditMode(
            self.app_window, self, self.label,
            multiline=True, markup=True, initial=self.value
        )

    def make_control_mode(self):
        return AltClickableControlMode(self.app_window, self, "Change text")

    async def configure(self, params):
        if params.get('value') is not None:
            new_text = params.get('value')
            if new_text != self.value:
                self.value = new_text
                self.set_text()

        if params.get('clickchange') is not None:
            self.clickchange = params['clickchange']

        if params.get('default') is not None:
            self.default = params['default']

        newsize = None
        if 'style' in params:
            newstyle = params.get('style')

        await super().configure(params)

        if newsize:
            await self.set_size(*newsize)

        if 'style' in params:
            newstyle = params['style']
            if 'font-face' in newstyle or 'font-size' in newstyle:
                self.label.set_font_name(self.get_fontspec())

        await self.update()
