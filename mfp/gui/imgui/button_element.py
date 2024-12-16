"""
imgui/button_element.py -- imgui backend for button elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from imgui_bundle import imgui, imgui_node_editor as nedit, ImVec4

from flopsy import mutates
from mfp import log
from ..colordb import ColorDB
from .base_element import ImguiBaseElementImpl

from ..button_element import (
    ButtonElement,
    ButtonElementImpl,
    BangButtonElement,
    BangButtonElementImpl,
    ToggleButtonElement,
    ToggleButtonElementImpl,
    ToggleIndicatorElement,
    ToggleIndicatorElementImpl,
)


class ImguiButtonElementImpl(ButtonElementImpl, ImguiBaseElementImpl, ButtonElement):
    backend_name = "imgui"

    style_defaults = {
        'padding': dict(left=8, top=6, right=8, bottom=6)
    }

    def __init__(self, window, x, y):
        super().__init__(window, x, y)
        self.node_id = None
        self.min_width = 16
        self.min_height = 16
        self.width = 16
        self.height = 16
        self.position_set = False

    @mutates('position_x', 'position_y', 'width', 'height')
    def render(self):
        """
        button element: similar to a message, but with an inner
        clickable box / state display
        """
        border_width = 1.25
        border_round = 2
        inset_size = 3

        # style
        padding = self.get_style('padding')
        padding_tpl = (
            padding.get('left', 0),
            padding.get('top', 0),
            padding.get('right', 0),
            padding.get('bottom', 0)
        )
        nedit.push_style_var(nedit.StyleVar.node_rounding, border_round)
        nedit.push_style_var(nedit.StyleVar.node_padding, ImVec4(*padding_tpl))
        nedit.push_style_var(nedit.StyleVar.node_border_width, border_width)

        nedit.push_style_color(
            nedit.StyleColor.node_bg,
            self.get_color('fill-color').to_rgbaf()
        )
        stroke_color = self.get_color('stroke-color')

        nedit.push_style_color(
            nedit.StyleColor.node_border,
            stroke_color.to_rgbaf()
        )
        need_recenter = False

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
            need_recenter = True

        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 0.0))

        self.render_sync_with_imgui()

        nedit.begin_node(self.node_id)

        # node content: nothing really, we are just going to draw on it
        imgui.begin_group()

        draw_list = imgui.get_window_draw_list()

        # draw the box
        corner = max(2, 0.1*min(self.width, self.height))

        if self.indicator:
            draw_list.add_rect_filled(
                [self.position_x + inset_size, self.position_y + inset_size],
                [self.position_x + self.width - inset_size, self.position_y + self.height - inset_size],
                ColorDB().backend.im_col32(stroke_color),
                rounding=corner,
                flags=0,
            )
        else:
            draw_list.add_rect(
                [self.position_x + inset_size, self.position_y + inset_size],
                [self.position_x + self.width - inset_size, self.position_y + self.height - inset_size],
                ColorDB().backend.im_col32(stroke_color),
                rounding=corner,
                flags=0,
                thickness=border_width
            )

        # render the label. It gets moved around to be centered.
        if self.indicator:
            self.label.set_color(self.get_color('text-color:lit'))
        else:
            self.label.set_color(self.get_color('text-color'))

        imgui.set_cursor_pos((
            self.position_x + self.label.position_x,
            self.position_y + self.label.position_y
        ))
        self.label.render()
        content_w, content_h = imgui.get_item_rect_size()

        if content_w + self.label.position_x < self.min_width:
            imgui.same_line()
            imgui.dummy([self.min_width - self.label.position_x - content_w, 1])

        if content_h + self.label.position_y < self.min_height:
            imgui.dummy([1, self.min_height - self.label.position_y - content_h])
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

        if need_recenter:
            self.center_label()

        # render
        ##########################

        imgui.pop_style_var()
        nedit.pop_style_color(2)  # color
        nedit.pop_style_var(3)  # padding, rounding

    def draw_ports(self):
        super().draw_ports()

    def redraw(self):
        pass

    @mutates('position_x', 'position_y')
    async def move(self, x, y, **kwargs):
        await super().move(x, y, **kwargs)

    async def delete(self, **kwargs):
        await super().delete(**kwargs)

    async def label_changed_cb(self, *args):
        pass

    async def set_size(self, width, height, **kwargs):
        await super().set_size(width, height, **kwargs)


class ImguiBangButtonElementImpl(BangButtonElement, BangButtonElementImpl, ImguiButtonElementImpl):
    backend_name = "imgui"


class ImguiToggleButtonElementImpl(ToggleButtonElement, ToggleButtonElementImpl, ImguiButtonElementImpl):
    backend_name = "imgui"


class ImguiToggleIndicatorElementImpl(
    ToggleIndicatorElement, ToggleIndicatorElementImpl, ImguiButtonElementImpl
):
    backend_name = "imgui"
