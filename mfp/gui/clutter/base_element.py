"""
clutter/BaseElement.py -- clutter backend for parent class of patch elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

import math
from gi.repository import Clutter

from mfp.gui_main import MFPGUI
from mfp.gui.base_element import BaseElement
from mfp.delegate import DelegateMixin, delegatemethod
from ..colordb import ColorDB
from ..backend_interfaces import BaseElementBackend

from mfp import log


class ClutterBaseElementBackend(BaseElement):
    backend_name = "clutter"

    def __init__(self, window, x, y):
        self.group = Clutter.Group()
        self.badge = None
        self.badge_times = {}
        self.badge_current = None
        self.port_elements = {}

        super().__init__(window, x, y)

    def move_to_top(self):
        def bump(element):
            if hasattr(element, 'backend'):
                actor = element.backend.group
            else:
                actor = element.group

            p = actor.get_parent()
            if not p:
                return
            p.remove_actor(actor)
            p.add_actor(actor)

        bump(self)
        for c in self.connections_out + self.connections_in:
            bump(c)

    def update_badge(self):
        badgesize = self.get_style('badge_size')
        if self.badge is None:
            self.badge = Clutter.CairoTexture.new(badgesize, badgesize)
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

    def draw_ports(self):
        if self.editable is False:
            return

        ports_done = []

        def confport(pid, px, py):
            pobj = self.port_elements.get(pid)
            dsp_port = False
            if (pid[0] == BaseElement.PORT_IN) and pid[1] in self.dsp_inlets:
                dsp_port = True

            if (pid[0] == BaseElement.PORT_OUT) and pid[1] in self.dsp_outlets:
                dsp_port = True

            if pobj is None:
                pobj = Clutter.Rectangle()
                pobj.set_size(
                    self.get_style('porthole_width'),
                    self.get_style('porthole_height')
                )
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
            confport(pid, x, y)

        for i in range(self.num_outlets):
            x, y = self.port_position(BaseElement.PORT_OUT, i)
            pid = (BaseElement.PORT_OUT, i)
            confport(pid, x, y)

        # clean up -- ports may need to be deleted if
        # the object resizes smaller
        for pid, port in list(self.port_elements.items()):
            if port not in ports_done:
                del self.port_elements[pid]
                self.group.remove_actor(port)

        # redraw connections
        for c in self.connections_out:
            c.draw()

        for c in self.connections_in:
            c.draw()

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

    def move(self, x, y):
        self.position_x = x
        self.position_y = y

        self.group.set_position(x, y)

        for c in self.connections_out:
            c.draw()

        for c in self.connections_in:
            c.draw()

    def move_z(self, z):
        self.position_z = z
        self.group.set_z_position(z)

    def set_size(self, width, height):
        super().set_size(width, height)
        Clutter.Group.set_size(self.group, width, height)
        self.update_badge()
