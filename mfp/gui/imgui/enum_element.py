"""
imgui/enum_element.py -- imgui backend for numeric/enumerated elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from imgui_bundle import imgui, imgui_node_editor as nedit
from flopsy import mutates

from .base_element import ImguiBaseElementImpl
from ..enum_element import (
    EnumElement,
    EnumElementImpl
)


class ImguiEnumElementImpl(EnumElementImpl, ImguiBaseElementImpl, EnumElement):
    backend_name = "imgui"

    style_defaults = {
        'padding': (12, 2, 4, 2)
    }

    def __init__(self, window, x, y):
        super().__init__(window, x, y)
        self.node_id = None
        self.width = 35
        self.height = 25

    @mutates('position_x', 'position_y', 'width', 'height')
    def render(self):
        """
        enum element

        * rectangle with square corners
        * triangle on left side
        * semicircular ports (only in edit mode)
        """
        # style
        nedit.push_style_var(nedit.StyleVar.node_rounding, 0.0)
        nedit.push_style_var(nedit.StyleVar.node_padding, self.get_style('padding'))
        nedit.push_style_var(nedit.StyleVar.node_border_width, 1)
        nedit.push_style_color(nedit.StyleColor.node_bg, (255, 255, 255, 255))

        ##########################
        # render
        if self.node_id is None:
            self.node_id = nedit.NodeId.create()
            self.position_set = False
            nedit.set_node_position(
                self.node_id,
                (self.position_x, self.position_y)
            )

        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 0.0))

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

        # status badge, if needed
        self.render_badge()

        nedit.end_node()

        # update size after render
        p_tl = imgui.get_item_rect_min()
        p_br = imgui.get_item_rect_max()

        self.width = p_br[0] - p_tl[0]
        self.height = p_br[1] - p_tl[1]
        self.position_x, self.position_y = (p_tl[0], p_tl[1])

        caret_off = 3.5
        caret_width = 5
        draw_list = imgui.get_window_draw_list()
        draw_list.add_convex_poly_filled(
            [
                (p_tl[0] + caret_off, p_tl[1] + caret_off),
                (p_tl[0] + caret_off + caret_width, p_tl[1] + self.height/2),
                (p_tl[0] + caret_off, p_tl[1] + self.height - caret_off),
            ],
            imgui.IM_COL32(150, 150, 150, 255)
        )

        # render
        ##########################

        imgui.pop_style_var()
        nedit.pop_style_color()  # color
        nedit.pop_style_var(3)

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

