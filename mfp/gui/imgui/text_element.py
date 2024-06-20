"""
imgui/text_element.py -- imgui backend for text (comment) elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from mfp.utils import catchall
from mfp.gui_main import MFPGUI
from imgui_bundle import imgui, imgui_node_editor as nedit
from ..colordb import ColorDB
from .base_element import ImguiBaseElementImpl
from ..text_element import (
    TextElement,
    TextElementImpl
)


class ImguiTextElementImpl(TextElementImpl, ImguiBaseElementImpl, TextElement):
    backend_name = "imgui"

    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        self.update_required = True
        self.width = 12
        self.height = 12
        self.position_set = False

    def render(self):
        # style
        nedit.push_style_var(nedit.StyleVar.node_rounding, 1.0)
        nedit.push_style_var(nedit.StyleVar.node_padding, (4, 2, 4, 2))
        nedit.push_style_color(
            nedit.StyleColor.node_bg,
            ColorDB().backend.im_colvec(self.get_color('fill-color'))
        )
        nedit.push_style_color(
            nedit.StyleColor.node_border,
            ColorDB().backend.im_colvec(self.get_color('border-color'))
        )
        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 0.0))

        if self.clickchange or self.get_style('border'):
            nedit.push_style_var(nedit.StyleVar.node_border_width, 1.0)
        else:
            nedit.push_style_var(nedit.StyleVar.node_border_width, 0)

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
        self.label.render()

        # connections
        self.render_ports()

        # status badge, if needed
        self.render_badge()

        nedit.end_node()
        imgui.pop_style_var()

        # update size after render
        p_tl = imgui.get_item_rect_min()
        p_br = imgui.get_item_rect_max()

        self.width = p_br[0] - p_tl[0]
        self.height = p_br[1] - p_tl[1]
        self.position_x, self.position_y = (p_tl[0], p_tl[1])

        # render
        ##########################

        nedit.pop_style_color(2)  # color
        nedit.pop_style_var(2)

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
