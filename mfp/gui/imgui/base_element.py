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
from .app_window.menu_bar import load_menupaths, add_menu_items


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
            self.position_x = None
            self.position_y = None
            self.position_z = None
            self.edit_mode = None
            self.editable = None
            self.container = None
            self.export_offset_x = None
            self.export_offset_y = None

        self.node_id = None

        self.badge = None
        self.badge_times = {}
        self.badge_current = None
        self.port_elements = {}

        self.tooltip_info = {}
        self.tooltip_timestamp = None

        self.selection_set = False
        self.position_set = False
        self.export_position_init = True
        self.export_container_x = None
        self.export_container_y = None

        self.hovered_state = False
        self.child_elements = []

        # data for code editor
        self.imgui_code_editor = None

        super().__init__(window, x, y)

    def select(self):
        self.selection_set = True
        return super().select()

    def unselect(self):
        self.selection_set = True
        return super().unselect()

    async def delete(self, **kwargs):
        children = self.child_elements
        self.child_elements = []
        for child in children:
            await child.delete(**kwargs)
        await super().delete(**kwargs)

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

    def get_stage_position(self):
        return (self.position_x, self.position_y)

    async def tooltip_update(self):
        info = await MFPGUI().mfp.get_tooltip_info(self.obj_id)
        self.tooltip_info = info
        self.tooltip_timestamp = datetime.now()
        self.update_badge()

    def show_on_panel(self):
        if isinstance(self.container, BaseElement):
            return self.panel_enable and self.container.show_on_panel()
        return self.panel_enable

    def calc_position(self):
        patch = self.layer.patch

        use_panel_pos = False
        if isinstance(self.container, BaseElement):
            use_panel_pos = True
        elif patch.panel_mode and self.show_on_panel():
            use_panel_pos = True

        if use_panel_pos:
            obj_x = self.panel_x
            obj_y = self.panel_y
            obj_z = self.panel_z
        else:
            obj_x = self.patch_x
            obj_y = self.patch_y
            obj_z = self.patch_z

        # element in an exported UI
        if isinstance(self.container, BaseElement):
            # subobject within a processor_element
            position_x = self.container.position_x + obj_x + self.export_offset_x
            position_y = self.container.position_y + obj_y + self.export_offset_y
            position_z = self.container.position_z + obj_z + 0.1
        # standalone top-level
        else:
            position_x = obj_x
            position_y = obj_y
            position_z = obj_z

        return (position_x, position_y, position_z)

    # every subclass should call this somewhere in the render method
    def render_sync_with_imgui(self):
        if isinstance(self.container, BaseElement):
            # we are creating a subobject within a processor_element
            if self.export_position_init:
                self.export_position_init = False
                self.position_x, self.position_y, self.position_z = self.calc_position()

                self.position_set = True
                self.export_container_x = self.container.position_x
                self.export_container_y = self.container.position_y
            # the containing processor_element has moved
            elif (
                self.container.position_x != self.export_container_x
                or self.container.position_y != self.export_container_y
            ):
                self.position_x, self.position_y, self.position_z = self.calc_position()
                self.position_set = True
                self.export_container_x = self.container.position_x
                self.export_container_y = self.container.position_y

        if self.position_set:
            self.position_set = False
            nedit.set_node_position(
                self.node_id,
                (self.position_x, self.position_y)
            )
            nedit.set_node_z_position(self.node_id, self.position_z)

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

    def render_sync_position(self, candidate_x, candidate_y):
        """
        there's something fishy with imgui-node-editor. Sometimes
        the node position jumps when calling begin_node. This
        helper checks at the end of the render cycle and filters
        out suspicious node movement.
        """
        if abs(candidate_x - self.position_x) > 5 or abs(candidate_y - self.position_y) > 5:
            log.debug(f"[render] position jump: was {(self.position_x, self.position_y)} now {(candidate_x, candidate_y)}, ignoring move")
        else:
            self.position_x = candidate_x
            self.position_y = candidate_y

    def render_badge(self):
        if not self.badge_current:
            return

        badgesize = self.get_style('badge-size')
        halfbadge = badgesize / 2.0
        ypos = 0
        xpos = self.width or self.min_width
        btext, bcolor = self.badge_current

        draw_list = imgui.get_window_draw_list()
        draw_list.add_circle_filled(
            (xpos + self.position_x, ypos + self.position_y),
            halfbadge,
            ColorDB().backend.im_col32(bcolor),
            24
        )
        draw_list.add_text(
            imgui.get_font(),
            14,
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
        pcolor = self.get_color('porthole-color')

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
        from mfp.gui.via_element import ViaElement

        if self.node_id is None:
            return
        if not self.selected and not self.editable:
            return

        if (
            not self.selected and self.container and self.container.panel_mode
            and self.panel_enable
            and not isinstance(self, ViaElement)
        ):
            return

        padding = self.get_style('padding')
        p_tl = imgui.get_item_rect_min()

        x_orig = p_tl[0] - padding.get('left', 0)
        y_orig = p_tl[1] - padding.get('top', 0)

        nedit.push_style_var(nedit.StyleVar.source_direction, (0, 0.5))
        nedit.push_style_var(nedit.StyleVar.target_direction, (0, -0.5))
        nedit.push_style_var(nedit.StyleVar.pin_rounding, 0)

        nedit.push_style_color(nedit.StyleColor.pin_rect_border, (0, 0, 0, 0.25))
        nedit.push_style_color(nedit.StyleColor.pin_rect, (0, 0, 0, 0.25))

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

    async def redraw_connections(self):
        pass

    @mutates('position_z')
    def move_z(self, z):
        self.position_z = z
