#! /usr/bin/env python
'''
patch_element.py
A patch element is the parent of all GUI entities backed by MFP objects

Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter
from mfp import MFPGUI, log
from .colordb import ColorDB
import math


class PatchElement (Clutter.Group):
    '''
    Parent class of elements represented in the patch window
    '''

    style_defaults = {
        'porthole_width': 8,
        'porthole_height': 4,
        'porthole_border': 1,
        'porthole_minspace': 11,
        'badge_size': 15,
        'badge-edit-color': 'default-edit-badge-color',
        'badge-learn-color': 'default-learn-badge-color',
        'badge-error-color': 'default-error-badge-color'
    }

    PORT_IN = 0
    PORT_OUT = 1

    OBJ_NONE = 0
    OBJ_HALFCREATED = 1
    OBJ_ERROR = 2
    OBJ_COMPLETE = 3
    OBJ_DELETED = 4
    TINY_DELTA = .0001

    def __init__(self, window, x, y):
        # MFP object and UI descriptors
        self.obj_id = None
        self.parent_id = None
        self.obj_name = None
        self.obj_type = None
        self.obj_args = None
        self.obj_state = self.OBJ_COMPLETE
        self.scope = None
        self.num_inlets = 0
        self.num_outlets = 0
        self.dsp_inlets = []
        self.dsp_outlets = []
        self.dsp_context = ""
        self.connections_out = []
        self.connections_in = []
        self.is_export = False
        self.param_list = ['position_x', 'position_y', 'width', 'height',
                           'update_required', 'display_type', 'name', 'layername',
                           'no_export', 'is_export', 'num_inlets', 'num_outlets', 'dsp_inlets',
                           'dsp_outlets', 'scope', 'style', 'export_offset_x',
                           'export_offset_y', 'debug']

        # Clutter objects
        self.stage = window
        self.container = None
        self.layer = None
        self.badge = None
        self.badge_times = {}
        self.badge_current = None
        self.port_elements = {}
        self.tags = {}

        # UI state
        self.position_x = x
        self.position_y = y
        self.position_z = 0
        self.export_offset_x = 0
        self.export_offset_y = 0
        self.width = None
        self.height = None
        self.drag_x = None
        self.drag_y = None
        self.selected = False
        self.editable = True
        self.debug = False
        self.update_required = False
        self.no_export = False
        self.edit_mode = None
        self.control_mode = None
        self.style = {}
        self._all_styles = self.combine_styles()

        # create placeholder group and add to stage
        Clutter.Group.__init__(self)

    def __repr__(self):
        return "<%s %s>" % (type(self).__name__, id(self))

    def corners(self):
        return [(self.position_x, self.position_y),
                (self.position_x + self.width, self.position_y),
                (self.position_x + self.width, self.position_y + self.height),
                (self.position_x, self.position_y + self.height)]

    @property
    def layername(self):
        return self.layer.name

    @property
    def name(self):
        return self.obj_name

    def get_style(self, propname):
        return self._all_styles.get(propname)

    def get_fontspec(self):
        return '{} {}px'.format(self.get_style('font-face'), self.get_style('font-size'))

    def get_color(self, colorspec):
        rgba = None
        if self.debug:
            rgba = self.get_style(colorspec + ':debug')
        elif self.selected:
            rgba = self.get_style(colorspec + ':selected')
        if not rgba:
            rgba = self.get_style(colorspec)
        if not rgba:
            rgba = self.get_style(colorspec.split(':')[0])

        if not rgba:
            log.error('Could not find color %s in %s' % (colorspec, self._all_styles))
            return ColorDB().find(64, 64, 64, 255)
        elif isinstance(rgba, str):
            return ColorDB().find(rgba)
        else:
            return ColorDB().find(rgba[0], rgba[1], rgba[2], rgba[3])

    def combine_styles(self):
        styles = {}
        for styleset in (MFPGUI().style_defaults, PatchElement.style_defaults,
                         type(self).style_defaults, self.style):
            styles.update(styleset)
        return styles

    def update(self):
        pass

    def event_source(self):
        return self

    def select(self):
        self.selected = True
        self.move_to_top()
        self.draw_ports()

    def unselect(self):
        self.selected = False
        self.draw_ports()

    def move_to_top(self):
        def bump(actor):
            p = actor.get_parent()
            if not p:
                return
            p.remove_actor(actor)
            p.add_actor(actor)

        bump(self)
        for c in self.connections_out + self.connections_in:
            bump(c)

    def drag_start(self, x, y):
        self.drag_x = x - self.position_x
        self.drag_y = y - self.position_y

    def move(self, x, y):
        self.position_x = x
        self.position_y = y

        self.set_position(x, y)

        for c in self.connections_out:
            c.draw()

        for c in self.connections_in:
            c.draw()

    def move_z (self, z):
        self.position_z = z
        self.set_z_position(z)

    def drag(self, dx, dy):
        self.move(self.position_x + dx, self.position_y + dy)

    def delete(self):
        self.stage.unregister(self)
        if self.obj_id is not None and not self.is_export:
            MFPGUI().mfp.delete.sync(self.obj_id)
        elif self.obj_id is None:
            for conn in [c for c in self.connections_out]:
                conn.delete()
            for conn in [c for c in self.connections_in]:
                conn.delete()

        self.obj_id = None
        self.obj_state = self.OBJ_DELETED

    def create(self, obj_type, init_args):
        scopename = self.layer.scope
        patchname = self.layer.patch.obj_name
        connections_out = self.connections_out
        connections_in = self.connections_in
        self.connections_out = []
        self.connections_in = []

        # FIXME: optional name-root argument?  Need to pass the number at all,
        # with the scope handling it?
        if self.obj_name is not None:
            name = self.obj_name
        else:
            name_index = self.stage.object_counts_by_type.get(self.display_type, 0)
            name = "%s_%03d" % (self.display_type, name_index)

        if self.obj_id is not None:
            MFPGUI().mfp.set_gui_created.sync(self.obj_id, False)
            MFPGUI().mfp.delete.sync(self.obj_id)
            self.obj_id = None

        objinfo = MFPGUI().mfp.create.sync(obj_type, init_args, patchname, scopename, name)
        if self.layer is not None and objinfo:
            objinfo["layername"] = self.layer.name

        if objinfo is None:
            self.stage.hud_write("ERROR: Could not create, see log for details")
            self.connections_out = connections_out
            self.connections_in = connections_in
            return None

        self.obj_id = objinfo.get('obj_id')
        self.obj_name = objinfo.get('name')
        self.obj_args = objinfo.get('initargs')
        self.obj_type = obj_type
        self.scope = objinfo.get('scope')
        self.num_inlets = objinfo.get("num_inlets")
        self.num_outlets = objinfo.get("num_outlets")
        self.dsp_inlets = objinfo.get("dsp_inlets", [])
        self.dsp_outlets = objinfo.get("dsp_outlets", [])

        if self.obj_id is not None:
            self.configure(objinfo)

            # rebuild connections if necessary
            for c in connections_in:
                if c.obj_2 is self and c.port_2 >= self.num_inlets:
                    c.obj_2 = None
                    c.delete()
                else:
                    self.connections_in.append(c)
                    if not c.dashed:
                        MFPGUI().mfp.connect.sync(c.obj_1.obj_id, c.port_1, c.obj_2.obj_id, c.port_2)

            for c in connections_out:
                if c.obj_1 is self and c.port_1 >= self.num_outlets:
                    c.obj_1 = None
                    c.delete()
                else:
                    self.connections_out.append(c)
                    if not c.dashed:
                        MFPGUI().mfp.connect.sync(c.obj_1.obj_id, c.port_1, c.obj_2.obj_id, c.port_2)

            MFPGUI().remember(self)
            self.send_params()
            MFPGUI().mfp.set_gui_created.sync(self.obj_id, True)

        self.stage.refresh(self)

        return self.obj_id

    def synced_params(self):
        prms = {}
        for k in self.param_list:
            prms[k] = getattr(self, k)
        return prms

    def send_params(self, **extras):
        if self.obj_id is None:
            return

        prms = self.synced_params()
        for k, v in extras.items():
            prms[k] = v

        MFPGUI().mfp.set_params.sync(self.obj_id, prms)

    def get_params(self):
        return MFPGUI().mfp.get_params.sync(self.obj_id)

    def get_stage_position(self):
        if not self.container or not self.layer or self.container == self.layer.group:
            return (self.position_x, self.position_y)
        else:
            pos_x = self.position_x
            pos_y = self.position_y

            c = self.container
            while isinstance(c, PatchElement):
                pos_x += c.position_x
                pos_y += c.position_y
                c = c.container

            return (pos_x, pos_y)

    def port_center(self, port_dir, port_num):
        ppos = self.port_position(port_dir, port_num)
        pos_x, pos_y = self.get_stage_position()

        return (pos_x + ppos[0] + 0.5 * self.get_style('porthole_width'),
                pos_y + ppos[1] + 0.5 * self.get_style('porthole_height'))

    def port_position(self, port_dir, port_num):
        w = self.get_width()
        h = self.get_height()
        if port_dir == PatchElement.PORT_IN:
            if self.num_inlets < 2:
                spc = 0
            else:
                spc = max(self.get_style('porthole_minspace'),
                          ((w - self.get_style('porthole_width')
                            - 2.0 * self.get_style('porthole_border'))
                           / (self.num_inlets - 1.0)))
            return (self.get_style('porthole_border') + spc * port_num, 0)

        elif port_dir == PatchElement.PORT_OUT:
            if self.num_outlets < 2:
                spc = 0
            else:
                spc = max(self.get_style('porthole_minspace'),
                          ((w - self.get_style('porthole_width')
                            - 2.0 * self.get_style('porthole_border'))
                           / (self.num_outlets - 1.0)))
            return (self.get_style('porthole_border') + spc * port_num,
                    h - self.get_style('porthole_height'))

    def draw_badge_cb(self, tex, ctx):
        tex.clear()
        if self.badge_current is None:
            return
        btext, bcolor = self.badge_current
        halfbadge = self.get_style('badge_size') / 2.0

        color = ColorDB.to_cairo(bcolor)
        ctx.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        ctx.move_to(halfbadge, halfbadge)
        ctx.arc(halfbadge, halfbadge, halfbadge, 0, 2*math.pi)
        ctx.fill()

        extents = ctx.text_extents(btext)
        color = ColorDB.to_cairo(ColorDB().find("white"))
        ctx.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        twidth = extents[4]
        theight = extents[3]

        ctx.move_to(halfbadge - twidth/2.0, halfbadge + theight/2.0)
        ctx.show_text(btext)

    def update_badge(self):
        badgesize = self.get_style('badge_size')
        if self.badge is None:
            self.badge = Clutter.CairoTexture.new(badgesize, badgesize)
            self.add_actor(self.badge)
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
            if (pid[0] == self.PORT_IN) and pid[1] in self.dsp_inlets:
                dsp_port = True

            if (pid[0] == self.PORT_OUT) and pid[1] in self.dsp_outlets:
                dsp_port = True

            if pobj is None:
                pobj = Clutter.Rectangle()
                pobj.set_size(self.get_style('porthole_width'),
                              self.get_style('porthole_height'))
                self.add_actor(pobj)
                self.port_elements[pid] = pobj

            if dsp_port:
                pobj.set_border_width(1.5)
                pobj.set_color(self.stage.color_bg)
                pobj.set_border_color(self.get_color('stroke-color'))
            else:
                pobj.set_color(self.get_color('stroke-color'))

            pobj.set_position(px, py)
            pobj.set_z_position(0.2)
            pobj.show()
            ports_done.append(pobj)

        for i in range(self.num_inlets):
            x, y = self.port_position(PatchElement.PORT_IN, i)
            pid = (PatchElement.PORT_IN, i)
            confport(pid, x, y)

        for i in range(self.num_outlets):
            x, y = self.port_position(PatchElement.PORT_OUT, i)
            pid = (PatchElement.PORT_OUT, i)
            confport(pid, x, y)

        # clean up -- ports may need to be deleted if
        # the object resizes smaller
        for pid, port in list(self.port_elements.items()):
            if port not in ports_done:
                del self.port_elements[pid]
                self.remove_actor(port)

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
            pid = (PatchElement.PORT_IN, i)
            hideport(pid)

        for i in range(self.num_outlets):
            pid = (PatchElement.PORT_OUT, i)
            hideport(pid)

    def command(self, action, data):
        pass

    def set_size(self, width, height):
        if (self.width and self.height
                and abs(width - self.width) < self.TINY_DELTA
                and abs(height - self.height) < self.TINY_DELTA):
            return

        self.width = width
        self.height = height
        Clutter.Group.set_size(self, self.width, self.height)
        self.update_badge()
        self.draw_ports()

        if self.obj_id and self.name:
            self.send_params()

    def configure(self, params):
        self.num_inlets = params.get("num_inlets", 0)
        self.num_outlets = params.get("num_outlets", 0)
        self.dsp_inlets = params.get("dsp_inlets", [])
        self.dsp_outlets = params.get("dsp_outlets", [])
        self.obj_name = params.get("name")
        self.no_export = params.get("no_export", False)
        self.is_export = params.get("is_export", False)
        self.export_offset_x = params.get("export_offset_x", 0)
        self.export_offset_y = params.get("export_offset_y", 0)
        self.debug = params.get("debug", False)

        newscope = params.get("scope", "__patch__")
        if (not self.scope) or newscope != self.scope:
            self.scope = newscope

        if params.get("tags") is not None and self.tags != params.get("tags"):
            self.tags = params.get("tags")
            self.update_badge()

        layer_name = params.get("layername") or params.get("layer")

        mypatch = ((self.layer and self.layer.patch)
                   or (self.stage and self.stage.selected_patch))
        layer = None
        if mypatch:
            layer = mypatch.find_layer(layer_name)

        if layer and self.layer != layer:
            self.move_to_layer(layer)

        if 'style' in params:
            self.style.update(params.get('style'))

        self._all_styles = self.combine_styles()

        w_orig, h_orig = self.get_size()

        w = params.get("width") or w_orig
        h = params.get("height") or h_orig

        if "position_x" in params and "position_y" in params:
            xpos = params['position_x']
            ypos = params['position_y']

            self.move(xpos, ypos)

        if "z_index" in params:
            self.move_z(params.get("z_index"))

        if (w != w_orig) or (h != h_orig):
            self.set_size(w, h)

        self.draw_ports()
        self.stage.refresh(self)


    def move_to_layer(self, layer):
        layer_child = False
        if layer and layer == self.layer:
            return
        elif self.layer:
            if self.get_parent() == self.layer.group:
                self.layer.group.remove_actor(self)
                self.container = None
                layer_child = True
            elif self.get_parent() is None:
                layer_child = True
            self.layer.remove(self)
        else:
            layer_child = True

        layer.add(self)
        if layer_child:
            self.layer.group.add_actor(self)
            self.container = self.layer.group
        self.send_params()

        for c in self.connections_out + self.connections_in:
            c.move_to_layer(layer)

    def make_edit_mode(self):
        return None

    def make_control_mode(self):
        return None

    def begin_edit(self):
        if not self.editable:
            return False

        if not self.edit_mode:
            self.edit_mode = self.make_edit_mode()

        if self.edit_mode:
            self.stage.input_mgr.enable_minor_mode(self.edit_mode)
        self.update_badge()

    def end_edit(self):
        if self.edit_mode:
            self.stage.input_mgr.disable_minor_mode(self.edit_mode)
            self.edit_mode = None
            self.stage.refresh(self)
        self.update_badge()

    def begin_control(self):
        if not self.control_mode:
            self.control_mode = self.make_control_mode()

        if self.control_mode:
            self.stage.input_mgr.enable_minor_mode(self.control_mode)

    def end_control(self):
        if self.control_mode:
            self.stage.input_mgr.disable_minor_mode(self.control_mode)
            self.control_mode = None

    def show_tip(self, xpos, ypos, details):
        tiptxt = None
        orig_x, orig_y = self.get_stage_position()

        if self.obj_id is None:
            return False

        for (pid, pobj) in self.port_elements.items():
            x, y = pobj.get_position()
            x += orig_x - 1
            y += orig_y - 1
            w, h = pobj.get_size()
            w += 2
            h += 2
            if (xpos >= x) and (xpos <= x+w) and (ypos >= y) and (ypos <= y+h):
                tiptxt = MFPGUI().mfp.get_tooltip.sync(self.obj_id, pid[0], pid[1], details)
        if tiptxt is None:
            tiptxt = MFPGUI().mfp.get_tooltip.sync(self.obj_id, None, None, details)
        self.stage.hud_banner(tiptxt)
        return True
