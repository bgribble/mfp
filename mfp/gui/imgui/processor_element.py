"""
imgui/processor_element.py -- imgui backend for processor elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from mfp import log
from flopsy import mutates

from mfp.gui_main import MFPGUI
from imgui_bundle import imgui, imgui_node_editor as nedit
from .base_element import ImguiBaseElementImpl
from ..processor_element import (
    ProcessorElement,
    ProcessorElementImpl,
)

ImColor = imgui.ImColor


class ImguiProcessorElementImpl(ProcessorElementImpl, ImguiBaseElementImpl, ProcessorElement):
    backend_name = "imgui"

    style_defaults = {
        'padding': (4, 2, 4, 6)
    }

    def __init__(self, window, x, y):
        super().__init__(window, x, y)
        self.node_id = None
        self.width = 35
        self.height = 25
        self.position_set = False

    @mutates('position_x', 'position_y', 'width', 'height')
    def render(self):
        """
        processor element

        * rectangle with hard corners
        * top and bottom "rails" containing ports
        * semicircular ports
        """

        # style
        nedit.push_style_var(nedit.StyleVar.node_rounding, 0.25)
        nedit.push_style_var(nedit.StyleVar.node_padding, self.get_style('padding'))
        nedit.push_style_var(nedit.StyleVar.node_border_width, 1)

        nedit.push_style_color(nedit.StyleColor.node_bg, (200, 200, 200, 255))
        nedit.push_style_color(nedit.StyleColor.hov_node_border, (80, 80, 80, 255))
        nedit.push_style_color(nedit.StyleColor.sel_node_border, (50, 50, 50, 255))

        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 0.0))
        ##########################
        # render
        if self.node_id is None:
            self.node_id = nedit.NodeId.create()
            self.position_set = False
            nedit.set_node_position(
                self.node_id,
                (self.position_x, self.position_y)
            )

        self.render_sync_with_imgui()

        nedit.begin_node(self.node_id)

        # node content: just the label
        imgui.begin_group()
        self.label.render()

        content_w, content_h = imgui.get_item_rect_size()

        if content_w < self.min_width:
            imgui.same_line()
            imgui.dummy([self.min_width - content_w, 1])

        if content_h < self.min_height:
            imgui.dummy([1, self.min_height - content_h])
        imgui.end_group()

        # connections
        self.render_ports()

        # status badge
        self.render_badge()

        nedit.end_node()

        # update size and position after render
        p_tl = imgui.get_item_rect_min()
        p_br = imgui.get_item_rect_max()

        self.width = p_br[0] - p_tl[0]
        self.height = p_br[1] - p_tl[1]
        self.position_x, self.position_y = (p_tl[0], p_tl[1])

        # render
        ##########################

        imgui.pop_style_var()
        nedit.pop_style_color(3)  # color
        nedit.pop_style_var(3)  # padding, rounding

    def draw_ports(self):
        super().draw_ports()

    @mutates('position_x', 'position_y')
    async def move(self, x, y, **kwargs):
        await super().move(x, y, **kwargs)

    async def delete(self, **kwargs):
        await super().delete(**kwargs)

    def redraw(self):
        super().redraw()

    async def label_changed_cb(self, *args):
        pass

    @mutates('width', 'height')
    async def set_size(self, width, height, **kwargs):
        await super().set_size(width, height, **kwargs)
