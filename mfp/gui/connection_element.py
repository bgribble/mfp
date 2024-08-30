"""
connection_element.py -- connection between elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from abc import ABCMeta, abstractmethod
from mfp.gui_main import MFPGUI

from .backend_interfaces import BackendInterface
from .base_element import BaseElement, ParamInfo


class ConnectionElementImpl(BackendInterface, metaclass=ABCMeta):
    @abstractmethod
    def redraw(self):
        pass


class ConnectionElement(BaseElement):
    display_type = "connection"
    LINE_WIDTH = 1.5

    # FIXME object state elements should be object types
    store_attrs = {
        **BaseElement.store_attrs,
        "rotation": ParamInfo(label="Rotation", param_type=float),
        "dashed": ParamInfo(label="Dashed", param_type=bool),
        "obj_1": ParamInfo(label="From object", param_type=int),
        "port_1": ParamInfo(label="From port", param_type=int),
        "obj_2": ParamInfo(label="To object", param_type=int),
        "port_2": ParamInfo(label="To port", param_type=int)
    }

    def __init__(self, window, position_x, position_y):

        self.obj_1 = None
        self.port_1 = None
        self.obj_2 = None
        self.port_2 = None
        self.width = None
        self.height = None
        self.rotation = 0.0
        self.dashed = False
        self.dsp_connect = False

        super().__init__(window, position_x, position_y)

    @classmethod
    def get_backend(cls, backend_name):
        return ConnectionElementImpl.get_backend(backend_name)

    @classmethod
    def build(cls, *args, **kwargs):
        window, obj_1, port_1, obj_2, port_2 = args
        dashed = kwargs.get("dashed", False)

        backend = cls.get_backend(MFPGUI().backend_name)
        px, py = obj_1.get_position()

        connection = backend(window, px, py)
        connection.connect(obj_1, port_1, obj_2, port_2, dashed)

        return connection

    def connect(self, obj_1, port_1, obj_2, port_2, dashed=False):
        self.obj_1 = obj_1
        self.port_1 = port_1
        self.obj_2 = obj_2
        self.port_2 = port_2
        self.dashed = dashed

        if port_1 in obj_1.dsp_outlets:
            self.dsp_connect = True
        self.redraw()

    async def delete(self, delete_obj=True):
        if (delete_obj and not self.dashed and self.obj_1 and self.obj_2 and
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
