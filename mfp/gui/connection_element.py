"""
connection_element.py -- connection between elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from abc import ABC, abstractmethod
from mfp.gui_main import MFPGUI

from .backend_interfaces import BackendInterface
from .base_element import BaseElement


class ConnectionElementImpl(ABC, BackendInterface):
    @abstractmethod
    def redraw(self):
        pass


class ConnectionElement(BaseElement):
    display_type = "connection"
    LINE_WIDTH = 1.5

    store_attrs = BaseElement.store_attrs + [
        "rotation", "dashed", "obj_1", "port_1", "obj_2", "port_2"
    ]

    def __init__(self, window, obj_1, port_1, obj_2, port_2, dashed=False):

        self.obj_1 = obj_1
        self.port_1 = port_1
        self.obj_2 = obj_2
        self.port_2 = port_2
        self.width = None
        self.height = None
        self.rotation = 0.0
        self.dashed = dashed
        self.dsp_connect = False

        if port_1 in obj_1.dsp_outlets:
            self.dsp_connect = True

        px, py = self.obj_1.get_position()
        super().__init__(window, px, py)

    @classmethod
    def get_factory(cls):
        return ConnectionElementImpl.get_backend(MFPGUI().appwin.backend_name)

    async def delete(self):
        if (not self.dashed and self.obj_1 and self.obj_2 and
                self.obj_1.obj_id is not None and self.obj_2.obj_id is not None):
            await MFPGUI().mfp.disconnect(
                self.obj_1.obj_id, self.port_1,
                self.obj_2.obj_id, self.port_2
            )
        if self.obj_1 and self in self.obj_1.connections_out:
            self.obj_1.connections_out.remove(self)
        if self.obj_2 and self in self.obj_2.connections_in:
            self.obj_2.connections_in.remove(self)

        self.obj_1 = None
        self.obj_2 = None
        await super().delete()
