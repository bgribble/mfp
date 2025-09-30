"""
imgui/button_element.py -- imgui backend for button elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from imgui_bundle import imgui, imgui_node_editor as nedit, ImVec4
from flopsy import mutates

from mfp import log
from mfp.gui_main import MFPGUI
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
        self.min_width = 20
        self.min_height = 20
        self.width = 20
        self.height = 20
        self.position_set = False
        self.indicator_triggered = 0

    @mutates('position_x', 'position_y', 'width', 'height')
    def render(self):
        """
        button element: similar to a message, but with an inner
        clickable box / state display
        """
        border_width = 1
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
        if self.indicator or self.indicator_triggered:
            draw_list.add_rect_filled(
                [
                    self.position_x + inset_size + border_width,
                    self.position_y + inset_size + border_width
                ],
                [
                    self.position_x + self.width - inset_size - border_width,
                    self.position_y + self.height - inset_size - border_width
                ],
                ColorDB().backend.im_col32(stroke_color),
                rounding=corner,
                flags=0,
            )
        else:
            draw_list.add_rect(
                [
                    self.position_x + inset_size,
                    self.position_y + inset_size
                ],
                [
                    self.position_x + self.width - inset_size,
                    self.position_y + self.height - inset_size
                ],
                ColorDB().backend.im_col32(stroke_color),
                rounding=corner,
                flags=0,
                thickness=border_width
            )

        # render the label. It gets moved around to be centered.
        if self.indicator or self.indicator_triggered:
            self.label.set_color(self.get_color('text-color:lit'))
        else:
            self.label.set_color(self.get_color('text-color'))

        label_rendered = True
        imgui.begin_group()
        if self.label_text or (self.edit_mode and self.edit_mode.enabled):
            imgui.set_cursor_pos((
                self.position_x + self.label.position_x,
                self.position_y + self.label.position_y
            ))
            self.label.render()
        else:
            label_rendered = False
            imgui.set_cursor_pos((
                self.position_x,
                self.position_y
            ))
            imgui.dummy([1, 1])
        imgui.end_group()

        content_w, content_h = imgui.get_item_rect_size()

        # real talk, I don't understand why I have to add these offsets
        # (16 and 13) to get the padding to work out right. But I do.
        x_pad = max(self.min_width - (content_w + 16), 0)
        y_pad = max(self.min_height - (content_h + 13), 0)

        imgui.same_line()
        imgui.dummy([x_pad, 1])
        imgui.dummy([1, y_pad])

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
        self.render_sync_position(p_tl[0], p_tl[1])

        if need_recenter:
            MFPGUI().async_task(self.center_label())

        self.indicator_triggered = max(0, self.indicator_triggered - 1)

        # render
        ##########################

        imgui.pop_style_var()
        nedit.pop_style_color(2)  # color
        nedit.pop_style_var(3)  # padding, rounding

    def draw_ports(self):
        super().draw_ports()

    def redraw(self):
        pass

    async def clicked(self, *args):
        await super().clicked(*args)
        self.indicator_triggered = 2
        return False

    @mutates('position_x', 'position_y')
    async def move(self, x, y, **kwargs):
        await super().move(x, y, **kwargs)

    async def delete(self, **kwargs):
        await super().delete(**kwargs)

    async def label_changed_cb(self, *args):
        pass

    async def set_size(self, width, height, **kwargs):
        await super().set_size(width, height, **kwargs)


class ImguiBangButtonElementImpl(ImguiButtonElementImpl, BangButtonElement, BangButtonElementImpl):
    backend_name = "imgui"


class ImguiToggleButtonElementImpl(ImguiButtonElementImpl, ToggleButtonElement, ToggleButtonElementImpl):
    backend_name = "imgui"


class ImguiToggleIndicatorElementImpl(
    ImguiButtonElementImpl, ToggleIndicatorElement, ToggleIndicatorElementImpl
):
    backend_name = "imgui"
