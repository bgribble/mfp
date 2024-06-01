"""
imgui/BaseElement.py -- imgui backend for parent class of patch elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

import math
from imgui_bundle import imgui, imgui_node_editor as nedit  # noqa
from flopsy import mutates  # noqa

from mfp import log

from mfp.gui_main import MFPGUI
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
            self.position_z = None
            self.edit_mode = None
            self.editable = None

        self.node_id = None

        self.badge = None
        self.badge_times = {}
        self.badge_current = None
        self.port_elements = {}

        super().__init__(window, x, y)

    def move_to_top(self):
        def bump(element):
            pass

        bump(self)
        for c in self.connections_out + self.connections_in:
            bump(c)

    def draw_ports(self):
        def semicircle_points(cx, cy, rx, ry, n, dir):
            return [
                (cx + rx * math.cos(k * math.pi / (n-1)),
                 cy + ry * dir * math.sin(k * math.pi / (n-1)))
                for k in range(n)
            ]

        port_rule = self.get_style("draw-ports") or "always"
        if port_rule == "never" or port_rule == "selected" and not self.selected:
            return

        if self.editable is False or self.node_id is None:
            return
        x_orig, y_orig = self.app_window.screen_to_canvas(self.position_x, self.position_y)

        draw_list = imgui.get_window_draw_list()
        ports_done = []

        def confport(pid, px, py):
            pin_id = self.port_elements.get(pid)
            dsp_port = False
            if (pid[0] == BaseElement.PORT_IN) and pid[1] in self.dsp_inlets:
                dsp_port = True

            if (pid[0] == BaseElement.PORT_OUT) and pid[1] in self.dsp_outlets:
                dsp_port = True

            if pin_id is None:
                pin_id = nedit.PinId.create()
                self.port_elements[pid] = pin_id

            nedit.push_style_var(nedit.StyleVar.pin_border_width, 2 if dsp_port else 1)
            nedit.begin_pin(
                pin_id,
                nedit.PinKind.input if pid[0] == BaseElement.PORT_IN else nedit.PinKind.output
            )

            pw = self.get_style('porthole_width')
            ph = self.get_style('porthole_height')

            nedit.pin_rect(
                (px, py), (px + pw, py + ph)
            )
            outport = pid[0] == BaseElement.PORT_OUT
            nedit.pin_pivot_rect(
                (px+pw/2, py + (ph if outport else 0)),
                (px+pw/2, py + (ph if outport else 0))
            )
            points = semicircle_points(
                px + pw / 2.0, py + (ph if outport else 0),
                pw / 2.0, ph,
                9, -1 if outport else 1
            )
            draw_list.add_convex_poly_filled(points, imgui.IM_COL32(255, 0, 0, 255))
            draw_list.add_polyline(points, imgui.IM_COL32(0, 0, 0, 100), 0, 1)

            """
            if dsp_port:
                pobj.set_border_width(1.5)
                pobj.set_color(MFPGUI().appwin.color_bg)
                pobj.set_border_color(self.get_color('stroke-color'))
            else:
                pobj.set_color(self.get_color('stroke-color'))
            """

            nedit.end_pin()
            nedit.pop_style_var()

            ports_done.append(pin_id)

        nedit.push_style_var(nedit.StyleVar.source_direction, (0, 0.5))
        nedit.push_style_var(nedit.StyleVar.target_direction, (0, -0.5))
        nedit.push_style_var(nedit.StyleVar.pin_rounding, 2)

        nedit.push_style_color(nedit.StyleColor.pin_rect_border, (0, 0, 0, 255))
        nedit.push_style_color(nedit.StyleColor.pin_rect, (0, 0, 0, 255))

        for i in range(self.num_inlets):
            x, y = self.port_position(BaseElement.PORT_IN, i)
            pid = (BaseElement.PORT_IN, i)
            confport(pid, x + x_orig, y + y_orig)

        for i in range(self.num_outlets):
            x, y = self.port_position(BaseElement.PORT_OUT, i)
            pid = (BaseElement.PORT_OUT, i)
            confport(pid, x + x_orig, y + y_orig)

        # clean up -- ports may need to be deleted if
        # the object resizes smaller
        for pid, port in list(self.port_elements.items()):
            if port not in ports_done:
                del self.port_elements[pid]

        nedit.pop_style_var(3)
        nedit.pop_style_color(2)

    def draw_badge_cb(self, tex, ctx):
        tex.clear()
        if self.badge_current is None:
            return
        btext, bcolor = self.badge_current
        halfbadge = self.get_style('badge_size') / 2.0

        color = ColorDB().normalize(bcolor)
        ctx.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        ctx.move_to(halfbadge, halfbadge)
        ctx.arc(halfbadge, halfbadge, halfbadge, 0, 2*math.pi)
        ctx.fill()

        extents = ctx.text_extents(btext)
        color = ColorDB().normalize(ColorDB().find("white"))
        ctx.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        twidth = extents[4]
        theight = extents[3]

        ctx.move_to(halfbadge - twidth/2.0, halfbadge + theight/2.0)
        ctx.show_text(btext)

    def update_badge(self):
        return

        badgesize = self.get_style('badge_size')
        if self.badge is None:
            self.badge = Clutter.CairoTexture.new(badgesize, badgesize)
            self.app_window.event_sources[self.badge] = self
            self.group.add_actor(self.badge)
            self.badge.connect("draw", self.draw_badge_cb)

        ypos = min(self.get_style('porthole_height') + self.get_style('porthole_border'),
                   self.height - badgesize / 2.0)
        self.badge.set_position(self.width - badgesize/2.0, ypos)
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

        self.badge.invalidate()

    def hide_ports(self):
        return

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

    async def redraw_connections(self):
        # redraw connections
        for c in self.connections_out:
            await c.draw()

        for c in self.connections_in:
            await c.draw()

    @mutates('position_z')
    def move_z(self, z):
        self.position_z = z
        self.group.set_z_position(z)
