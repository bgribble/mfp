#! /usr/bin/env python
'''
message_element.py
A patch element corresponding to a clickable message

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from abc import ABCMeta, abstractmethod
from flopsy import saga
from mfp.gui_main import MFPGUI
from .text_widget import TextWidget
from .base_element import BaseElement
from .connection_element import ConnectionElement
from .backend_interfaces import BackendInterface
from .modes.label_edit import LabelEditMode
from .modes.transient import TransientMessageEditMode
from .modes.clickable import ClickableControlMode


class MessageElementImpl(BackendInterface, metaclass=ABCMeta):
    @abstractmethod
    def redraw(self):
        pass


class MessageElement (BaseElement):
    display_type = "message"
    proc_type = "message"

    label_off_x = 4
    label_off_y = 1

    PORT_TWEAK = 5

    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        self.message_text = None
        self.clickstate = False
        self.update_required = True

        self.obj_state = self.OBJ_HALFCREATED

        # configure label
        self.label = TextWidget.build(self)
        self.label.set_position(self.label_off_x, self.label_off_y)
        self.label.set_color(self.get_color('text-color'))
        self.label.set_font_name(self.get_fontspec())
        self.label.set_reactive(False)

    @classmethod
    def get_backend(cls, backend_name):
        return MessageElementImpl.get_backend(backend_name)

    @saga('obj_args')
    async def recreate_element(self, action, state_diff, previous):
        if "obj_state" in state_diff and state_diff['obj_state'][0] == None:
            return

        if self.obj_type:
            yield await self.label_edit_finish(None, f"{self.obj_args}")

    async def update(self):
        self.redraw()
        self.draw_ports()

    async def clicked(self, *args):
        self.clickstate = True
        if self.obj_id is not None:
            MFPGUI().async_task(MFPGUI().mfp.send_bang(self.obj_id, 0))
        self.redraw()
        return False

    def unclicked(self):
        self.clickstate = False
        self.redraw()
        return False

    async def set_size(self, width, height, **kwargs):
        return await super().set_size(width, height, **kwargs)

    async def label_edit_start(self):
        self.obj_state = self.OBJ_HALFCREATED
        await self.update()

    async def label_edit_finish(self, widget=None, text=None):
        if text is not None and text != self.message_text:
            self.message_text = text
            await self.create(self.proc_type, self.message_text)

        if self.obj_id is not None:
            self.obj_state = self.OBJ_COMPLETE
            self.send_params()
            await self.update()

    async def configure(self, params):
        if params.get('value') is not None:
            self.message_text = repr(params.get('value'))
            self.label.set_text(self.message_text)
            params['width'] = None
            params['height'] = None
        elif self.obj_args is not None:
            self.message_text = self.obj_args
            self.label.set_text(self.obj_args)
            params['width'] = None
            params['height'] = None

        if self.obj_state != self.OBJ_COMPLETE and self.obj_id is not None:
            self.obj_state = self.OBJ_COMPLETE
            await self.update()
        await super().configure(params)

    def select(self):
        BaseElement.select(self)
        if self.label:
            self.label.set_color(self.get_color('text-color'))
        self.redraw()

    def unselect(self):
        BaseElement.unselect(self)
        if self.label:
            self.label.set_color(self.get_color('text-color'))
        self.redraw()

    async def make_edit_mode(self):
        return LabelEditMode(self.app_window, self, self.label)

    def make_control_mode(self):
        return ClickableControlMode(self.app_window, self, "Message control")


class TransientMessageElementImpl(BackendInterface, metaclass=ABCMeta):
    @abstractmethod
    def redraw(self):
        pass


class TransientMessageElement (MessageElement):
    ELBOW_ROOM = 50

    def __init__(self, window, x, y):
        self.target_obj = [t for t in window.selected if t is not self]
        self.target_port = 0

        pos_x, pos_y = self.target_obj[0].get_stage_position()
        super().__init__(window, pos_x, pos_y - self.ELBOW_ROOM)

        self.message_text = "Bang"
        self.num_inlets = 0
        self.num_outlets = 1
        self.label.set_text(self.message_text)
        self.obj_state = self.OBJ_COMPLETE
        self.draw_ports()

        self._make_connections()

    @classmethod
    def get_backend(cls, backend_name):
        return TransientMessageElementImpl.get_backend(backend_name)

    def _make_connections(self):
        for to in self.target_obj:
            c = ConnectionElement.build(self.app_window, self, 0, to, self.target_port)
            c.move_to_layer(self.app_window.active_layer())
            self.app_window.register(c)
            self.connections_out.append(c)
            to.connections_in.append(c)

    async def set_port(self, portnum):
        if portnum == self.target_port:
            return True

        self.target_port = portnum

        for c in self.connections_out:
            await c.delete()

        self._make_connections()
        return True

    async def end_edit(self):
        await BaseElement.end_edit(self)
        if self.obj_state == self.OBJ_COMPLETE:
            await self.delete()

    async def label_edit_start(self):
        self.label.set_text(self.message_text)
        self.label.set_selection(0, len(self.message_text))
        await self.update()

    async def label_edit_finish(self, widget=None, text=None):
        if text is not None:
            self.message_text = text
            for to in self.target_obj:
                if to is not self:
                    await MFPGUI().mfp.eval_and_send(
                        to.obj_id,
                        self.target_port,
                        self.message_text
                    )
        for to in self.target_obj:
            await self.app_window.select(to)
        self.message_text = None
        await self.delete()

    async def make_edit_mode(self):
        return TransientMessageEditMode(self.app_window, self, self.label)
