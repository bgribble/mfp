"""
imgui/text_element.py -- imgui backend for text (comment) elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from flopsy import mutates
from imgui_bundle import imgui, imgui_node_editor as nedit, ImVec4

from mfp import log
from mfp.gui.base_element import BaseElement
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
        self.min_width = 12
        self.min_height = 12
        self.position_set = False

    @mutates('position_x', 'position_y', 'width', 'height')
    def render(self):
        from mfp.gui.modes.patch_edit import PatchEditMode

        # style
        nedit.push_style_var(nedit.StyleVar.node_rounding, 1.0)
        nedit.push_style_var(nedit.StyleVar.node_padding, ImVec4(4, 2, 4, 2))
        nedit.push_style_color(
            nedit.StyleColor.node_bg,
            self.get_color('fill-color').to_rgbaf()
        )
        nedit.push_style_color(
            nedit.StyleColor.node_border,
            self.get_color('stroke-color').to_rgbaf()
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
            nedit.set_node_z_position(self.node_id, self.position_z)

        self.render_sync_with_imgui()

        nedit.begin_node(self.node_id)

        # node content: just the label
        imgui.begin_group()

        tile = self.layer.patch.display_info
        if isinstance(self.container, BaseElement):
            parent = self.container
            total = parent.export_w
            available = total - (self.position_x - parent.position_x)
            clip_w = available
            padding = 0
        elif self.edit_mode and self.edit_mode.enabled:
            total = tile.width / tile.view_zoom
            available = total - (self.position_x - tile.view_x)
            clip_w = available
            padding = 10 / tile.view_zoom
        else:
            total = tile.width / tile.view_zoom
            available = min(self.width or self.min_width, self.max_width)
            clip_w = total - (self.position_x - tile.view_x)
            padding = 0

        clip_h = (tile.height / tile.view_zoom) - (self.position_y - tile.view_y)

        wrap_width = max(
            min(self.max_width, available - padding),
            self.min_width
        )

        imgui.begin_table(
            f"##{self.node_id}__table",
            1,
            imgui.TableFlags_.sizing_fixed_fit,
            (wrap_width, 0)
        )
        imgui.table_setup_column("content", 0, wrap_width)
        imgui.table_next_row()
        imgui.table_set_column_index(0)

        # render the content and measure it. hopefully smaller
        # than the wrap-table
        imgui.begin_group()
        self.label.render(wrap_width=wrap_width)
        imgui.end_group()
        imgui.end_table()
        content_w, content_h = imgui.get_item_rect_size()

        if content_w < self.min_width:
            imgui.same_line()
            imgui.dummy([self.min_width - content_w, 1])

        if content_h < self.min_height:
            imgui.dummy([1, self.min_height - content_h])

        eff_width = min(max(content_w, self.min_width), self.max_width)

        imgui.end_group()
        self.width = eff_width

        if not self.height:
            self.height = self.min_height

        # connections
        self.render_ports()

        # status badge, if needed
        self.render_badge()

        nedit.end_node()
        imgui.pop_style_var()

        # update size after render
        p_tl = imgui.get_item_rect_min()
        p_br = imgui.get_item_rect_max()

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

    @mutates('width', 'height')
    async def set_size(self, width, height, **kwargs):
        await super().set_size(width, height, **kwargs)
