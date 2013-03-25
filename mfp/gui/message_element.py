#! /usr/bin/env python2.6
'''
message_element.py
A patch element corresponding to a clickable message

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter
import cairo
from mfp import MFPGUI

from .patch_element import PatchElement
from .connection_element import ConnectionElement
from .modes.label_edit import LabelEditMode
from .modes.transient import TransientMessageEditMode
from .modes.clickable import ClickableControlMode
from .colordb import ColorDB 

class MessageElement (PatchElement):
    display_type = "message"
    proc_type = "message"

    PORT_TWEAK = 5

    def __init__(self, window, x, y):
        PatchElement.__init__(self, window, x, y)

        self.message_text = None
        self.clickstate = False

        # create elements
        self.texture = Clutter.CairoTexture.new(35, 25)
        self.label = Clutter.Text()

        self.texture.set_size(35, 25)
        self.texture.connect("draw", self.draw_cb)

        self.set_reactive(True)
        self.add_actor(self.texture)
        self.add_actor(self.label)

        self.set_size(35, 25)
        self.obj_state = self.OBJ_HALFCREATED
        self.texture.invalidate()

        # configure label
        self.label.set_position(4, 1)
        self.label.set_color(window.color_unselected)
        self.label.connect('text-changed', self.text_changed_cb)

        self.move(x, y)

        # request update when value changes
        self.update_required = True

    def set_size(self, width, height):
        PatchElement.set_size(self, width, height)
        self.texture.set_size(width, height)
        self.texture.set_surface_size(width, height)
        self.texture.invalidate()

    def draw_cb(self, texture, ct):
        if self.clickstate:
            lw = 5.0
        else:
            lw = 2.0

        w = self.texture.get_property('surface_width') - lw
        h = self.texture.get_property('surface_height') - lw
        c = None
        texture.clear()

        if self.obj_state == self.OBJ_COMPLETE:
            ct.set_dash([])
        else:
            ct.set_dash([8, 4])

        ct.set_line_width(lw)

        ct.set_antialias(cairo.ANTIALIAS_NONE)
        ct.translate(lw / 2.0, lw / 2.0)
        # ct.set_line_width(1.25)
        ct.move_to(0, 0)
        ct.line_to(0, h)
        ct.line_to(w, h)
        ct.curve_to(w - 8, h - 8, w - 8, 8, w, 0)
        ct.line_to(0, 0)
        ct.close_path()

        # fill to paint the background 
        c = ColorDB.to_cairo(self.color_bg)
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        ct.fill_preserve()

        # stroke to draw the outline 
        c = ColorDB.to_cairo(self.color_fg)
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        ct.stroke()

    def update(self):
        self.draw_ports()
        self.texture.invalidate()

    def clicked(self, *args):
        self.clickstate = True
        if self.obj_id is not None:
            MFPGUI().mfp.send_bang(self.obj_id, 0)
        self.texture.invalidate()
        return False

    def unclicked(self):
        self.clickstate = False
        self.texture.invalidate()
        return False

    def label_edit_start(self):
        self.obj_state = self.OBJ_HALFCREATED
        self.texture.invalidate()

    def label_edit_finish(self, widget=None, text=None):
        if text is not None and text != self.message_text:
            self.message_text = text
            self.create(self.proc_type, self.message_text)

        if self.obj_id is not None:
            self.obj_state = self.OBJ_COMPLETE
            self.send_params()
            self.update()

    def text_changed_cb(self, *args):
        lwidth = self.label.get_property('width')
        bwidth = self.texture.get_property('surface_width')

        new_w = None
        if (lwidth > (bwidth - 20)):
            new_w = lwidth + 20
        elif (bwidth > 35) and (lwidth < (bwidth - 20)):
            new_w = max(35, lwidth + 20)

        if new_w is not None:
            self.set_size(new_w, self.texture.get_height())
            self.texture.set_size(new_w, self.texture.get_height())
            self.texture.set_surface_size(int(new_w), 
                                          self.texture.get_property('surface_height'))
            self.update()

    def configure(self, params):
        if params.get('value') is not None:
            self.label.set_text(repr(params.get('value')))
        elif self.obj_args is not None:
            self.label.set_text(self.obj_args)

        if self.obj_state != self.OBJ_COMPLETE and self.obj_id is not None:
            self.obj_state = self.OBJ_COMPLETE
            self.update()

        PatchElement.configure(self, params)

    def port_position(self, port_dir, port_num):
        # tweak the right input port display to be left of the "kick"
        if port_dir == PatchElement.PORT_IN and port_num == 1:
            default = PatchElement.port_position(self, port_dir, port_num)
            return (default[0] - self.PORT_TWEAK, default[1])
        else:
            return PatchElement.port_position(self, port_dir, port_num)

    def select(self):
        PatchElement.select(self)
        self.texture.invalidate()

    def unselect(self):
        PatchElement.unselect(self)
        self.texture.invalidate()

    def delete(self):
        for c in self.connections_out + self.connections_in:
            c.delete()
        PatchElement.delete(self)

    def make_edit_mode(self):
        return LabelEditMode(self.stage, self, self.label)

    def make_control_mode(self):
        return ClickableControlMode(self.stage, self, "Message control")


class TransientMessageElement (MessageElement):
    ELBOW_ROOM = 50

    def __init__(self, window, x, y):
        self.target_obj = window.selected
        self.target_port = None

        MessageElement.__init__(self, window, self.target_obj[0].position_x,
                                self.target_obj[0].position_y - self.ELBOW_ROOM)
        self.message_text = "Bang"
        self.num_inlets = 0
        self.num_outlets = 1 
        self.label.set_text(self.message_text)
        self.obj_state = self.OBJ_COMPLETE 
        self.draw_ports()
        self.set_port(0)

    def set_port(self, portnum):
        if portnum == self.target_port:
            return True

        for c in self.connections_out:
            c.delete()

        self.target_port = portnum
        for to in self.target_obj: 
            c = ConnectionElement(self.stage, self, 0, to, self.target_port)
            self.connections_out.append(c)
            to.connections_in.append(c)

        return True

    def label_edit_start(self):
        self.label.set_text(self.message_text)
        self.label.set_selection(0, len(self.message_text))
        self.texture.invalidate()

    def label_edit_finish(self, widget=None, text=None):
        if text is not None:
            self.message_text = text 
            for to in self.target_obj:
                if to is not self:
                    MFPGUI().mfp.eval_and_send(to.obj_id, self.target_port,
                                               self.message_text)
        for to in self.target_obj:
            self.stage.select(to)
        self.delete()

    def make_edit_mode(self):
        return TransientMessageEditMode(self.stage, self, self.label)
