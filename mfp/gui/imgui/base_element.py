"""
imgui/BaseElement.py -- imgui backend for parent class of patch elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

import math
from datetime import datetime
from imgui_bundle import imgui, imgui_node_editor as nedit
from flopsy import mutates

from mfp import log
from mfp.gui_main import MFPGUI
from mfp.gui.event import EnterEvent, LeaveEvent
from mfp.gui.base_element import BaseElement, BaseElementImpl
from ..colordb import ColorDB


class ImguiBaseElementImpl(BaseElementImpl):
    backend_name = "imgui"

    def __init__(self, window, x, y):
        # instance vars that are actually declared in BaseElement
        if not hasattr(self, 'app_window'):
            self.app_window = None
            self.connections_out = []
            self.connections_in = []
            self.dsp_inlets = []
            self.dsp_outlets = []
            self.num_inlets = None
            self.num_outlets = None
            self.tags = {}
            self.width = None
            self.height = None
            self.min_width = 0
            self.min_height = 0
            self.position_z = None
            self.edit_mode = None
            self.editable = None

        self.node_id = None

        self.badge = None
        self.badge_times = {}
        self.badge_current = None
        self.port_elements = {}

        self.tooltip_info = {}
        self.tooltip_timestamp = None

        self.selection_set = False
        self.position_set = False

        self.hovered_state = False

        super().__init__(window, x, y)

    def select(self):
        self.selection_set = True
        return super().select()

    def unselect(self):
        self.selection_set = True
        return super().unselect()

    # position_x and position_y need special handling because
    # the imgui canvas can change them independently
    def _SET_POSITION_X(self, new_pos, previous=None):
        self.position_set = True
        if previous:
            old_pos = previous.get("position_x")
        else:
            old_pos = self.position_x

        self.position_x = new_pos
        return "position_x", old_pos

    def _SET_POSITION_Y(self, new_pos, previous=None):
        self.position_set = True
        if previous:
            old_pos = previous.get("position_y")
        else:
            old_pos = self.position_y

        self.position_y = new_pos
        return "position_y", old_pos

    async def move(self, x, y, **kwargs):
        self.position_set = True
        await super().move(x, y, **kwargs)

    def move_to_top(self):
        def bump(element):
            pass

        bump(self)
        for c in self.connections_out + self.connections_in:
            bump(c)

    async def tooltip_update(self):
        info = await MFPGUI().mfp.get_tooltip_info(self.obj_id)
        self.tooltip_info = info
        self.tooltip_timestamp = datetime.now()

    # every subclass should call this somewhere in the render method
    def render_sync_with_imgui(self):
        if self.position_set:
            self.position_set = False
            nedit.set_node_position(
                self.node_id,
                (self.position_x, self.position_y)
            )

        # check hover
        if nedit.get_hovered_node() == self.node_id:
            hovered = True
        else:
            hovered = False

        if hovered and not self.hovered_state:
            self.hovered_state = True
            MFPGUI().async_task(
                self.app_window.signal_emit("enter-event", EnterEvent(target=self))
            )
        if not hovered and self.hovered_state:
            self.hovered_state = False
            MFPGUI().async_task(
                self.app_window.signal_emit("leave-event", LeaveEvent(target=self))
            )

        # check selection status
        if self.selection_set:
            self.selection_set = False
            if self.selected:
                if not nedit.is_node_selected(self.node_id):
                    nedit.select_node(self.node_id)
            else:
                if nedit.is_node_selected(self.node_id):
                    nedit.deselect_node(self.node_id)
        else:
            if nedit.is_node_selected(self.node_id):
                if not self.selected:
                    MFPGUI().async_task(self.app_window.select(self))
                    self.selected = True
            else:
                if self.selected:
                    MFPGUI().async_task(self.app_window.unselect(self))
                    self.selected = False

    def render_badge(self):
        if not self.badge_current:
            return

        badgesize = self.get_style('badge-size')
        halfbadge = badgesize / 2.0
        ypos = 0
        xpos = self.width
        btext, bcolor = self.badge_current

        draw_list = imgui.get_window_draw_list()
        draw_list.add_circle_filled(
            (xpos + self.position_x, ypos + self.position_y),
            halfbadge,
            ColorDB().backend.im_col32(bcolor),
            24
        )
        draw_list.add_text(
            (xpos - halfbadge/2.0 + self.position_x + 0.5, ypos - halfbadge + self.position_y + 0.5),
            imgui.IM_COL32(255, 255, 255, 255),
            btext
        )

    def render_port(self, port_id, px, py, dsp_port):
        def semicircle_points(cx, cy, rx, ry, n, direction):
            yoff = -ry if direction > 0 else 0
            return [
                (
                    cx + rx * math.cos(k * math.pi / (n-1)),
                    cy + ry * direction * math.sin(k * math.pi / (n-1)) + yoff
                )
                for k in range(n)
            ]

        out_port = port_id[0] == BaseElement.PORT_OUT
        draw_list = imgui.get_window_draw_list()

        pw = self.get_style('porthole-width')
        ph = self.get_style('porthole-height')
        pcolor = self.get_style('porthole-color')

        points = semicircle_points(
            px,
            py + (ph if out_port else 0),
            pw / 2.0, ph,
            9,
            1 if out_port else -1
        )
        if dsp_port:
            draw_list.add_polyline(
                points,
                ColorDB().backend.im_col32(pcolor),
                imgui.ImDrawFlags_.closed, 
                1.0,
            )
        else:
            draw_list.add_convex_poly_filled(
                points, 
                ColorDB().backend.im_col32(pcolor)
            )

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
        nedit.pin_rect(
            (px - pw/2, py + (0 if outport else -ph)),
            (px + pw/2, py + ph + (0 if outport else -ph))
        )
        nedit.pin_pivot_rect(
            (px, py), (px, py)
        )
        port_rule = self.get_style("draw-ports") or "always"
        draw_ports = port_rule != "never" and (port_rule != "selected" or self.selected)
        if draw_ports:
            self.render_port(port_id, px, py, dsp_port)
        nedit.end_pin()
        nedit.pop_style_var()

    def render_ports(self):
        if self.editable is False or self.node_id is None:
            return

        p_tl = imgui.get_item_rect_min()
        padding = self.get_style('padding')

        # FIXME hardcoded padding
        x_orig = p_tl[0] - padding[0]
        y_orig = p_tl[1] - padding[1]

        nedit.push_style_var(nedit.StyleVar.source_direction, (0, 0.5))
        nedit.push_style_var(nedit.StyleVar.target_direction, (0, -0.5))
        nedit.push_style_var(nedit.StyleVar.pin_rounding, 0)

        nedit.push_style_color(nedit.StyleColor.pin_rect_border, (0, 0, 0, 100))
        nedit.push_style_color(nedit.StyleColor.pin_rect, (0, 0, 0, 100))

        ports_done = []
        for i in range(self.num_inlets):
            x, y = self.port_position(BaseElement.PORT_IN, i)
            pid = (BaseElement.PORT_IN, i)
            self.render_pin(pid, x + x_orig, y + y_orig)
            ports_done.append(pid)

        for i in range(self.num_outlets):
            x, y = self.port_position(BaseElement.PORT_OUT, i)
            pid = (BaseElement.PORT_OUT, i)
            self.render_pin(pid, x + x_orig, y + y_orig)
            ports_done.append(pid)

        # clean up -- ports may need to be deleted if
        # the object resizes smaller
        for pid, port in list(self.port_elements.items()):
            if pid not in ports_done:
                del self.port_elements[pid]

        nedit.pop_style_color(2)
        nedit.pop_style_var(3)

    def update_badge(self):
        tagged = False

        if self.edit_mode:
            self.badge_current = ("E", self.get_color('badge-edit-color'))
            tagged = True
        else:
            self.badge_current = None

        if not tagged and "midi" in self.tags:
            if self.tags["midi"] == "learning":
                self.badge_current = ("M", self.get_color('badge-learn-color'))
                tagged = True
            else:
                self.badge_current = None

        if not tagged and "osc" in self.tags:
            if self.tags["osc"] == "learning":
                self.badge_current = ("O", self.get_color('badge-learn-color'))
                tagged = True
            else:
                self.badge_current = None

        if not tagged and "errorcount" in self.tags:
            ec = self.tags["errorcount"]
            if ec > 9:
                ec = "!"
            elif ec > 0:
                ec = "%d" % ec
            if ec:
                self.badge_current = (ec, self.get_color('badge-error-color'))
                tagged = True


    def hide_ports(self):
        return
    """
            def hideport(pid):
                pobj = self.port_elements.get(pid)
                if pobj:
                    pobj.hide()

            for i in range(self.num_inlets):
                pid = (BaseElement.PORT_IN, i)
                hideport(pid)

            for i in range(self.num_outlets):
                pid = (BaseElement.PORT_OUT, i)
                hideport(pid)
    """

    async def redraw_connections(self):
        pass


    @mutates('position_z')
    def move_z(self, z):
        self.position_z = z
        self.group.set_z_position(z)
