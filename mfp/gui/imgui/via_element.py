"""
imgui/via_element.py == Imgui implementation of via elements

send/receive, signal/control - 4 types total

Copyright (c) Bill Gribble <grib@billgribble.com>
"""
from flopsy import mutates
from imgui_bundle import imgui, imgui_node_editor as nedit, ImVec4
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
        self.position_remainder = 0.0
        self.position_set = False

    @mutates('position_x')
    def recenter_label(self, *args):
        if not args:
            return
        widget, signal, old_text, new_text, old_size, new_size = args
        if old_size[0] != new_size[0]:
            desired = self.position_x + (old_size[0] - new_size[0]) / 2.0
            desired += self.position_remainder
            self.position_remainder = desired % 1.0
            self.position_x = float(int(desired))
            self.position_set = True

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
        nedit.push_style_var(nedit.StyleVar.node_padding, ImVec4(4, 2, 4, 2))
        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 0.0))
        nedit.push_style_color(
            nedit.StyleColor.node_bg,
            ColorDB().find('transparent').to_rgbaf()

        )
        nedit.push_style_color(
            nedit.StyleColor.node_border,
            ColorDB().find('transparent').to_rgbaf()
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

        self.render_sync_with_imgui()

        nedit.begin_node(self.node_id)

        # node content: label plus space for the via blob
        imgui.begin_group()
        if self.display_type in ('sendvia', 'sendsignalvia'):
            imgui.dummy((1, self.VIA_SIZE - 1))
        self.label.render()

        if self.display_type in ('recvvia', 'recvsignalvia'):
            imgui.dummy((1, self.VIA_SIZE))
        imgui.end_group()

        # update size before ports
        content_tl = imgui.get_item_rect_min()
        content_br = imgui.get_item_rect_max()

        self.width = content_br[0] - content_tl[0]
        self.height = content_br[1] - content_tl[1]

        # draw ports
        self.render_ports()

        # status badge, if needed
        self.render_badge()

        nedit.end_node()

        # update size after render
        p_tl = imgui.get_item_rect_min()
        p_br = imgui.get_item_rect_max()

        self.width = p_br[0] - p_tl[0]
        self.height = p_br[1] - p_tl[1]
        self.render_sync_position(p_tl[0], p_tl[1])

        # render
        ##########################

        nedit.pop_style_color(2)  # color
        imgui.pop_style_var()
        nedit.pop_style_var(5)

    def draw_ports(self):
        super().draw_ports()

    def render_port(self, port_id, px, py, dsp_port):
        draw_list = imgui.get_window_draw_list()

        outport = False
        pw = self.get_style('porthole-width')
        half_height = self.get_style('porthole-height') / 2.0

        stroke_color = imgui.IM_COL32(*self.get_color('stroke-color').to_rgba())

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
                (px + pw / 2, py + half_height * (-1 if outport else 1)),
                arcsize,
                stroke_color,
                24,
                linewidth
            )
        else:
            draw_list.add_circle_filled(
                (px + pw / 2, py + half_height * (-1 if outport else 1)),
                arcsize,
                stroke_color,
                24
            )

        if self.GLYPH_STYLE.endswith("circled"):
            draw_list.add_circle(
                (px + pw / 2, py + half_height * (-1 if outport else 1)),
                self.VIA_SIZE / 2.0,
                stroke_color,
                24,
                linewidth
            )

    def port_position(self, port_dir, port_num):
        if port_num == 0:
            px = self.width / 2.0
            py = 0
            if port_dir == BaseElement.PORT_OUT:
                py = self.height
        else:
            px = self.width
            py = self.height / 2.0
        return px, py

    def port_center(self, port_dir, port_num):
        pos_x, pos_y = self.get_stage_position()

        ppos = self.port_position(port_dir, port_num)
        pw = self.get_style('porthole-width')
        xoff = 0 if port_dir == BaseElement.PORT_OUT else pw
        return pos_x + self.width / 2 - xoff, pos_y + ppos[1]

    def render_pin(self, port_id, px, py):
        pin_id = self.port_elements.get(port_id)
        dsp_port = False
        if (port_id[0] == BaseElement.PORT_IN) and port_id[1] in self.dsp_inlets:
            dsp_port = True

        if (port_id[0] == BaseElement.PORT_OUT) and port_id[1] in self.dsp_outlets:
            dsp_port = True

        if pin_id is None:
            pin_id = nedit.PinId.create()
            self.port_elements[port_id] = pin_id

        nedit.push_style_var(nedit.StyleVar.pin_border_width, 1)
        nedit.begin_pin(
            pin_id,
            nedit.PinKind.input if port_id[0] == BaseElement.PORT_IN else nedit.PinKind.output
        )

        pw = self.get_style('porthole-width')
        ph = self.get_style('porthole-height')

        outport = port_id[0] == BaseElement.PORT_OUT


        if self.GLYPH_STYLE in ("empty_circled", "filled_circled"):
            offset = 1 if not outport else -1
        else:
            offset = 0

        nedit.pin_rect(
            (px, py - (ph if outport else 0)),
            (px + pw, py + ph - (ph if outport else 0)),
        )
        nedit.pin_pivot_rect(
            (px + pw/2, py + offset),
            (px + pw/2, py + offset)
        )
        port_rule = self.get_style("draw-ports") or "always"
        draw_ports = port_rule != "never" and (port_rule != "selected" or self.selected) and port_id[1] == 0
        if draw_ports:
            self.render_port(port_id, px, py, dsp_port)
        nedit.end_pin()
        nedit.pop_style_var()


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
