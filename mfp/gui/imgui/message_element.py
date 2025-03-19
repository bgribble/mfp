"""
imgui/message_element.py -- imgui backend for message elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from flopsy import mutates
from mfp import log
from mfp.gui_main import MFPGUI
from imgui_bundle import imgui, imgui_node_editor as nedit, ImVec4
from .base_element import ImguiBaseElementImpl
from ..message_element import (
    MessageElement,
    MessageElementImpl,
    PatchMessageElement,
    PatchMessageElementImpl,
    TransientMessageElement,
    TransientMessageElementImpl
)


class ImguiMessageElementImpl(MessageElementImpl, ImguiBaseElementImpl, MessageElement):
    backend_name = "imgui"

    style_defaults = {
        'porthole-border': 6,  # allow for rounded corners
        'padding': dict(left=4, top=2, right=4, bottom=2)
    }

    def __init__(self, window, x, y):
        super().__init__(window, x, y)
        self.node_id = None
        self.min_width = self.width = 25
        self.min_height = self.height = 12
        self.click_triggered = False

    @mutates('position_x', 'position_y', 'width', 'height')
    def render(self):
        """
        message element

        * rectangle with rounded corners
        * gradient background
        """
        # style
        padding = self.get_style('padding')
        padding_tpl = (
            padding.get('left', 0),
            padding.get('top', 0),
            padding.get('right', 0),
            padding.get('bottom', 0)
        )
        nedit.push_style_var(nedit.StyleVar.node_rounding, 4.0)
        nedit.push_style_var(nedit.StyleVar.node_padding, ImVec4(*padding_tpl))
        nedit.push_style_var(nedit.StyleVar.node_border_width, 1.25)

        fill_color = "fill-color"
        stroke_color = "stroke-color"
        text_color = "text-color"
        if self.click_triggered:
            fill_color = "fill-color:lit"
            text_color = "text-color:lit"
            self.click_triggered = False

        nedit.push_style_color(
            nedit.StyleColor.node_bg,
            self.get_color(fill_color).to_rgbaf()
        )
        nedit.push_style_color(
            nedit.StyleColor.node_border,
            self.get_color(stroke_color).to_rgbaf()
        )

        ##########################
        # render
        if self.node_id is None:
            self.node_id = nedit.NodeId.create()
            self.position_set = False
            nedit.set_node_position(
                self.node_id,
                (self.position_x, self.position_y)
            )
            nedit.set_node_z_position(self.node_id, self.position_z)

        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 0.0))

        self.render_sync_with_imgui()

        nedit.begin_node(self.node_id)

        # node content: just the label
        imgui.begin_group()
        self.label.render(highlight=self.highlight_text)

        content_w, content_h = imgui.get_item_rect_size()

        if content_w < self.min_width:
            imgui.same_line()
            imgui.dummy([self.min_width - content_w, 1])

        if content_h < self.min_height:
            imgui.dummy([1, self.min_height - content_h])
        imgui.end_group()

        # connections
        self.render_ports()

        # status badge, is needed
        self.render_badge()

        nedit.end_node()

        # update size after render
        p_tl = imgui.get_item_rect_min()
        p_br = imgui.get_item_rect_max()

        self.width = p_br[0] - p_tl[0]
        self.height = p_br[1] - p_tl[1]
        self.position_x, self.position_y = (p_tl[0], p_tl[1])

        # render
        ##########################

        imgui.pop_style_var()
        nedit.pop_style_color(2)  # color
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

    async def clicked(self, *args):
        await super().clicked(*args)
        self.click_triggered = True
        return False

class ImguiPatchMessageElementImpl(
    PatchMessageElement,
    ImguiMessageElementImpl,
    PatchMessageElementImpl,
):
    backend_name = "imgui"


class ImguiTransientMessageElementImpl(
    TransientMessageElement,
    ImguiMessageElementImpl,
    TransientMessageElementImpl,
):
    backend_name = "imgui"
