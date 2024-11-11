"""
clutter/BaseElement.py -- clutter backend for parent class of patch elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

import math
from gi.repository import Clutter
from flopsy import mutates, saga

from mfp.gui_main import MFPGUI
from mfp.gui.base_element import BaseElement, BaseElementImpl
from ..colordb import ColorDB


class ClutterBaseElementImpl(BaseElementImpl):
    backend_name = "clutter"

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

        self.group = Clutter.Group.new()
        self.badge = None
        self.badge_times = {}
        self.badge_current = None
        self.port_elements = {}

        super().__init__(window, x, y)

    async def delete(self, **kwargs):
        await super().delete(**kwargs)

        if self.badge:
            if self.badge in self.app_window.event_sources:
                del self.app_window.event_sources[self.badge]
            self.badge.destroy()
            self.badge = None

        for port in self.port_elements.values():
            port.destroy()

        self.port_elements = {}

        if self.group:
            if self.group in self.app_window.event_sources:
                del self.app_window.event_sources[self.group]
            self.group.destroy()
            self.group = None

    def move_to_top(self):
        def bump(element):
            actor = element.group

            if not actor:
                return

            p = actor.get_parent()
            if not p:
                return

            p.remove_actor(actor)
            p.add_actor(actor)

        bump(self)
        for c in self.connections_out + self.connections_in:
            bump(c)

    def draw_badge_cb(self, tex, ctx):
        tex.clear()
        if self.badge_current is None:
            return
        btext, bcolor = self.badge_current
        halfbadge = self.get_style('badge-size') / 2.0

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
        if self.group is None:
            return

        badgesize = self.get_style('badge-size')
        if self.badge is None:
            self.badge = Clutter.CairoTexture.new(badgesize, badgesize)
            self.app_window.event_sources[self.badge] = self
            self.group.add_actor(self.badge)
            self.badge.connect("draw", self.draw_badge_cb)

        ypos = min(self.get_style('porthole-height') + self.get_style('porthole-border'),
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

    def draw_ports(self):
        port_rule = self.get_style("draw-ports") or "always"
        if port_rule == "never" or port_rule == "selected" and not self.selected:
            return

        if self.editable is False or self.group is None:
            return

        ports_done = []
        port_height = self.get_style('porthole-height')
        port_width = self.get_style('porthole-width')
        
        def confport(pid, px, py):
            pobj = self.port_elements.get(pid)
            dsp_port = False
            if (pid[0] == BaseElement.PORT_IN) and pid[1] in self.dsp_inlets:
                dsp_port = True

            if (pid[0] == BaseElement.PORT_OUT) and pid[1] in self.dsp_outlets:
                dsp_port = True

            if pobj is None:
                pobj = Clutter.Rectangle()
                pobj.set_size(port_width, port_height)
                self.group.add_actor(pobj)
                self.port_elements[pid] = pobj

            if dsp_port:
                pobj.set_border_width(1.5)
                pobj.set_color(MFPGUI().appwin.color_bg)
                pobj.set_border_color(self.get_color('stroke-color'))
            else:
                pobj.set_color(self.get_color('stroke-color'))

            pobj.set_position(px, py)
            pobj.set_z_position(0.2)
            pobj.show()
            ports_done.append(pobj)

        for i in range(self.num_inlets):
            x, y = self.port_position(BaseElement.PORT_IN, i)
            pid = (BaseElement.PORT_IN, i)
            confport(pid, x - port_width / 2, y)

        for i in range(self.num_outlets):
            x, y = self.port_position(BaseElement.PORT_OUT, i)
            pid = (BaseElement.PORT_OUT, i)
            confport(pid, x - port_width / 2, y - port_height)

        # clean up -- ports may need to be deleted if
        # the object resizes smaller
        for pid, port in list(self.port_elements.items()):
            if port not in ports_done:
                del self.port_elements[pid]
                self.group.remove_actor(port)

        MFPGUI().async_task(self.redraw_connections())

    def hide_ports(self):
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

    async def move(self, x, y, **kwargs):
        await super().move(x, y, **kwargs)

        if not self.group:
            return

        self.group.set_position(x, y)

        for c in self.connections_out:
            await c.draw(update_state=kwargs.get("update_state", True))

        for c in self.connections_in:
            await c.draw(update_state=kwargs.get("update_state", True))

    @mutates('position_z')
    def move_z(self, z):
        self.position_z = z
        self.group.set_z_position(z)

    async def set_size(self, width, height, **kwargs):
        await super().set_size(width, height, **kwargs)
        Clutter.Group.set_size(self.group, width, height)
        self.update_badge()
