"""
imgui/connection_element.py -- imgui backend for connection elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from imgui_bundle import imgui, imgui_node_editor as nedit

from ..colordb import ColorDB
from mfp.gui.base_element import BaseElement
from .base_element import ImguiBaseElementImpl
from ..connection_element import (
    ConnectionElement,
    ConnectionElementImpl,
)


class ImguiConnectionElementImpl(ConnectionElementImpl, ImguiBaseElementImpl, ConnectionElement):
    backend_name = "imgui"

    def __init__(self, window, position_x, position_y):
        super().__init__(window, position_x, position_y)

    def render(self):
        """
        mostly we will be letting the ingui_node_editor handle links
        """
        if not self.node_id:
            self.node_id = nedit.LinkId.create()

        nedit.link(
            self.node_id,
            self.obj_1.port_elements[
                (BaseElement.PORT_OUT, self.port_1)
            ],
            self.obj_2.port_elements[
                (BaseElement.PORT_IN, self.port_2)
            ],
            (0, 0, 255, 255),
            1,
        )

    def draw_ports(self):
        super().draw_ports()

    async def move(self, x, y, **kwargs):
        await super().move(x, y, **kwargs)

    async def delete(self, **kwargs):
        await super().delete(**kwargs)

    def redraw(self):
        super().redraw()

    async def label_changed_cb(self, *args):
        pass

    async def set_size(self, width, height, **kwargs):
        await super().set_size(width, height, **kwargs)
