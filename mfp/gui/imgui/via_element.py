"""
imgui/via_element.py == Imgui implementation of via elements

send/receive, signal/control - 4 types total

Copyright (c) Bill Gribble <grib@billgribble.com>
"""
from flopsy import mutates
from imgui_bundle import imgui, imgui_node_editor as nedit


from ..colordb import ColorDB
from ..base_element import BaseElement
from ..via_element import (
    SendViaElement,
    SendViaElementImpl,
    SendSignalViaElement,
    SendSignalViaElementImpl,
    ReceiveViaElement,
    ReceiveViaElementImpl,
    ReceiveSignalViaElement,
    ReceiveSignalViaElementImpl
)
from .base_element import ImguiBaseElementImpl


class ImguiBaseViaElementImpl(ImguiBaseElementImpl):
    backend_name = "imgui"

    GLYPH_STYLE = "none"
    VIA_SIZE = 10
    VIA_FUDGE = 5
    LABEL_HEIGHT = 15
    LABEL_FUDGE = 0
    LABEL_Y = 0

    style_defaults = {
        'porthole-width': 8,
        'porthole-height': 8,
    }

    def __init__(self, window, x, y):
        self.label = None
        super().__init__(window, x, y)
        self.position_x = x
        self.position_y = y
        self.position_set = False

    def recenter_label(self):
        """
        w = self.label.get_width()
        _, y = self.label.get_position()
        self.label.set_position((self.texture.get_width() - w) / 2.0, y)
        """

    @mutates('position_x', 'position_y', 'width', 'height')
    def render(self):
        """
        via element - no node drawn, just the label and the port
        """
        # style
        nedit.push_style_var(nedit.StyleVar.node_rounding, 0)
        nedit.push_style_var(nedit.StyleVar.node_border_width, 0)
        nedit.push_style_var(nedit.StyleVar.hovered_node_border_width, 0.0)
        nedit.push_style_var(nedit.StyleVar.selected_node_border_width, 0.0)
        nedit.push_style_var(nedit.StyleVar.node_padding, (4, 2, 4, 2))
        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 0.0))
        nedit.push_style_color(
            nedit.StyleColor.node_bg, (255, 255, 255, 0)
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

        self.render_sync_with_imgui()

        nedit.begin_node(self.node_id)

        # node content: just the label
        self.label.render()

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

        # render
        ##########################

        nedit.pop_style_color()  # color
        imgui.pop_style_var()
        nedit.pop_style_var(5)

    def draw_ports(self):
        super().draw_ports()

    def render_port(self, port_id, px, py, dsp_port):
        draw_list = imgui.get_window_draw_list()

        outport = False
        pw = self.VIA_SIZE
        half_height = self.get_style('porthole-height') / 2.0

        stroke_color = self.get_color('stroke-color').to_rgba()

        if self.GLYPH_STYLE in ("empty_circled", "filled_circled"):
            arcsize = self.VIA_SIZE / 3.5
            linewidth = 1
        else:
            arcsize = self.VIA_SIZE / 2.0
            linewidth = 3

        if port_id[0] == BaseElement.PORT_IN:
            if self.display_type in ('recvvia', 'recvsignalvia'):
                return
        elif port_id[0] == BaseElement.PORT_OUT:
            outport = True
            if self.display_type in ('sendvia', 'sendsignalvia'):
                return

        if self.GLYPH_STYLE.startswith("empty"):
            draw_list.add_circle(
                (px, py + half_height * (1 if outport else -1)),
                arcsize,
                stroke_color,
                24,
                linewidth
            )
        else:
            draw_list.add_circle_filled(
                (px, py + half_height * (1 if outport else -1)),
                arcsize,
                stroke_color,
                24
            )

        if self.GLYPH_STYLE.endswith("circled"):
            draw_list.add_circle(
                (px, py + half_height * (1 if outport else -1)),
                pw / 2.0,
                stroke_color,
                24,
                linewidth
            )

    def port_position(self, port_dir, port_num):
        px = self.width / 2.0
        py = 0
        if port_dir == BaseElement.PORT_OUT:
            py += self.height
        return px, py

    @mutates('position_x', 'position_y')
    async def move(self, x, y, **kwargs):
        await super().move(x, y, **kwargs)

    async def delete(self, **kwargs):
        await super().delete(**kwargs)

    def redraw(self):
        pass

    async def label_changed_cb(self, *args):
        pass

    @mutates('width', 'height')
    async def set_size(self, width, height, **kwargs):
        await super().set_size(width, height, **kwargs)


class ImguiSendViaElementImpl(SendViaElementImpl, ImguiBaseViaElementImpl, SendViaElement):
    GLYPH_STYLE = "empty"
    LABEL_Y = ImguiBaseViaElementImpl.VIA_SIZE + ImguiBaseViaElementImpl.VIA_FUDGE / 2.0
    TEXTURE_Y = 0

    def redraw(self):
        ImguiBaseViaElementImpl.redraw(self)


class ImguiSendSignalViaElementImpl(
    SendSignalViaElementImpl, ImguiBaseViaElementImpl, SendSignalViaElement
):
    VIA_SIZE = 12
    GLYPH_STYLE = "empty_circled"
    LABEL_Y = ImguiBaseViaElementImpl.VIA_SIZE + ImguiBaseViaElementImpl.VIA_FUDGE / 2.0
    TEXTURE_Y = 0

    def redraw(self):
        ImguiBaseViaElementImpl.redraw(self)


class ImguiReceiveViaElementImpl(
    ReceiveViaElementImpl, ImguiBaseViaElementImpl, ReceiveViaElement
):
    GLYPH_STYLE = "filled"
    LABEL_Y = 0
    LABEL_FUDGE = 2.5
    TEXTURE_Y = ImguiBaseViaElementImpl.LABEL_HEIGHT + LABEL_FUDGE

    def redraw(self):
        ImguiBaseViaElementImpl.redraw(self)


class ImguiReceiveSignalViaElementImpl(
    ReceiveSignalViaElementImpl, ImguiBaseViaElementImpl, ReceiveSignalViaElement
):
    VIA_SIZE = 12
    GLYPH_STYLE = "filled_circled"
    LABEL_Y = 0
    LABEL_FUDGE = 2.5
    TEXTURE_Y = ImguiBaseViaElementImpl.LABEL_HEIGHT + LABEL_FUDGE

    def redraw(self):
        ImguiBaseViaElementImpl.redraw(self)
