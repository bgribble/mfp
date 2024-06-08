"""
imgui/message_element.py -- imgui backend for message elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""
import math

from mfp import log
from mfp.gui_main import MFPGUI
from imgui_bundle import imgui, imgui_node_editor as nedit
from .base_element import ImguiBaseElementImpl
from ..message_element import (
    MessageElement,
    MessageElementImpl,
)

ImColor = imgui.ImColor


class ImguiMessageElementImpl(MessageElementImpl, ImguiBaseElementImpl, MessageElement):
    backend_name = "imgui"

    style_defaults = {
        'porthole_border': 6  # allow for rounded corners
    }

    def __init__(self, window, x, y):
        super().__init__(window, x, y)
        self.node_id = None
        self.width = 35
        self.height = 25

    def render(self):
        """
        message element

        * rectangle with rounded corners
        * gradient background
        * semicircular ports (only in edit mode)
        """
        # style
        nedit.push_style_var(nedit.StyleVar.node_rounding, 6.0)
        nedit.push_style_var(nedit.StyleVar.node_padding, (6, 4, 6, 8))
        nedit.push_style_color(nedit.StyleColor.node_bg, (255, 255, 255, 255))
        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 0.0))

        ##########################
        # render
        if self.node_id is None:
            self.node_id = nedit.NodeId.create()
            nedit.set_node_position(
                self.node_id,
                self.app_window.screen_to_canvas(self.position_x, self.position_y)
            )

        # check selection status
        if nedit.is_node_selected(self.node_id):
            if not self.selected:
                log.debug(f"[render] node {self} becomes selected")
                MFPGUI().async_task(self.app_window.select(self))
                self.selected = True
        else:
            if self.selected:
                log.debug(f"[render] node {self} becomes unselected")
                MFPGUI().async_task(self.app_window.unselect(self))
                self.selected = False

        nedit.begin_node(self.node_id)

        # node content: just the label
        self.label.render()

        # connections
        self.render_ports()

        nedit.end_node()
        imgui.pop_style_var()

        # update size after render
        p_tl = imgui.get_item_rect_min()
        p_br = imgui.get_item_rect_max()

        self.width = p_br[0] - p_tl[0]
        self.height = p_br[1] - p_tl[1]
        self.position_x, self.position_y = self.app_window.canvas_to_screen(p_tl[0], p_tl[1])

        # render
        ##########################

        nedit.pop_style_color()  # color
        nedit.pop_style_var()

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

