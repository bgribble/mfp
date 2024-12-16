"""
imgui/connection_element.py -- imgui backend for connection elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from imgui_bundle import imgui, imgui_node_editor as nedit

from flopsy import mutates
from mfp import log
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
        if self.selection_set:
            self.selection_set = False
            if self.selected:
                if not nedit.is_link_selected(self.node_id):
                    nedit.select_link(self.node_id)
            else:
                if nedit.is_link_selected(self.node_id):
                    nedit.deselect_link(self.node_id)

        complete_color = self.get_color('link-color')
        snoop_color = self.get_color('link-color:snoop')
        dashed_color = (1, 1, 1, 0.5)

        if self.dashed:
            thickness = 1
            color = dashed_color
            nedit.push_style_var(nedit.StyleVar.flow_marker_distance, 30)
            nedit.push_style_var(nedit.StyleVar.flow_speed, 25)
            nedit.push_style_var(nedit.StyleVar.flow_duration, 0.1)
        elif self.dsp_connect:
            thickness = 3
            color = complete_color.to_rgbaf()
        elif self.snoop:
            thickness = 2
            color = snoop_color.to_rgbaf()
        else:
            thickness = 1.5
            color = complete_color.to_rgbaf()

        nedit.link(
            self.node_id,
            from_port_obj,
            to_port_obj,
            color,
            thickness
        )

        if self.dashed:
            nedit.flow(self.node_id)
            nedit.pop_style_var(3)
            self.app_window.imgui_prevent_idle = 1

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
