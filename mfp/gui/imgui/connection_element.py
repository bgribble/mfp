"""
imgui/connection_element.py -- imgui backend for connection elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from imgui_bundle import imgui, imgui_node_editor as nedit

from flopsy import mutates

from mfp.gui_main import MFPGUI
from mfp.gui.colordb import ColorDB
from mfp.gui.base_element import BaseElement
from .base_element import ImguiBaseElementImpl
from mfp.gui.connection_element import (
    ConnectionElement,
    ConnectionElementImpl,
)


class ImguiConnectionElementImpl(ConnectionElementImpl, ImguiBaseElementImpl, ConnectionElement):
    backend_name = "imgui"

    def __init__(self, window, position_x, position_y):
        super().__init__(window, position_x, position_y)

    @mutates('position_x', 'position_y', 'width', 'height')
    def render(self):
        """
        mostly we will be letting the imgui_node_editor handle links
        """
        if not self.node_id:
            self.node_id = nedit.LinkId.create()

        from_port_obj = self.obj_1.port_elements.get(
            (BaseElement.PORT_OUT, self.port_1 or 0)
        )
        to_port_obj = self.obj_2.port_elements.get(
            (BaseElement.PORT_IN, self.port_2 or 0)
        )
        if not from_port_obj or not to_port_obj:
            return

        # check selection status
        if nedit.is_link_selected(self.node_id):
            if not self.selected:
                MFPGUI().async_task(self.app_window.select(self))
                self.selected = True
        else:
            if self.selected:
                MFPGUI().async_task(self.app_window.unselect(self))
                self.selected = False
        complete_color = (0, 0, 255, 255)
        dashed_color = (40, 40, 80, 255)

        nedit.link(
            self.node_id,
            from_port_obj,
            to_port_obj,
            dashed_color if self.dashed else complete_color,
            1 if not self.dsp_connect else 3,
        )

    def draw_ports(self):
        super().draw_ports()

    @mutates('position_x', 'position_y')
    async def move(self, x, y, **kwargs):
        await super().move(x, y, **kwargs)

    async def delete(self, **kwargs):
        await super().delete(**kwargs)

    def redraw(self):
        super().redraw()

    async def draw(self):
        pass

    async def label_changed_cb(self, *args):
        pass

    @mutates('width', 'height')
    async def set_size(self, width, height, **kwargs):
        await super().set_size(width, height, **kwargs)
