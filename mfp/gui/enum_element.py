#! /usr/bin/env python2.6
'''
enum_element.py
A patch element corresponding to a number box or enum selector

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter
import cairo
import math
from patch_element import PatchElement
from mfp import MFPGUI
from .modes.enum_control import EnumEditMode, EnumControlMode


class EnumElement (PatchElement):
    display_type = "enum"
    proc_type = "enum"

    PORT_TWEAK = 7

    def __init__(self, window, x, y):
        PatchElement.__init__(self, window, x, y)

        self.value = 0
        self.digits = 1
        self.min_value = None
        self.max_value = None 
        self.scientific = False
        self.format_str = "%.1f"
        self.connections_out = []
        self.connections_in = []
        self.editable = False
        self.update_required = True

        self.param_list.remove('width')
        self.param_list.remove('height')
        self.param_list.extend(['digits', 'min_value', 'max_value', 'scientific'])

        self.obj_state = self.OBJ_HALFCREATED

        # create elements
        self.texture = Clutter.CairoTexture.new(35, 25)
        self.texture.connect("draw", self.draw_cb)
        self.label = Clutter.Text()

        self.set_reactive(True)
        self.add_actor(self.texture)
        self.add_actor(self.label)

        # configure label
        self.label.set_position(4, 1)
        self.label.set_color(window.color_unselected)
        self.label.connect('text-changed', self.text_changed_cb)
        self.label.set_text(self.format_value(self.value))

        # click handler
        # self.actor.connect('button-press-event', self.button_press_cb)

        self.move(x, y)
        self.texture.invalidate()

    def format_update(self):
        if self.scientific:
            oper = "e"
        else:
            oper = "f"
        self.format_str = "%%.%d%s" % (self.digits, oper)

    def format_value(self, value):
        if self.min_value is not None and value < self.min_value:
            value = self.min_value 
        if self.max_value is not None and value > self.max_value:
            value = self.max_value 
        return self.format_str % value

    def draw_cb(self, texture, ct):
        w = self.texture.get_property('surface_width') - 1
        h = self.texture.get_property('surface_height') - 1
        self.texture.clear()
        if self.selected:
            color = self.stage.color_selected
        else:
            color = self.stage.color_unselected

        if self.obj_state == self.OBJ_COMPLETE:
            ct.set_dash([])
        else:
            ct.set_dash([8, 4])

        ct.set_line_width(2.0)
        ct.set_antialias(cairo.ANTIALIAS_NONE)
        ct.set_source_rgba(color.red, color.green, color.blue, 1.0)
        ct.translate(0.5, 0.5)
        ct.move_to(1, 1)
        ct.line_to(1, h)
        ct.line_to(w, h)
        ct.line_to(w, h / 3.0 + 1)
        ct.line_to(w - h / 3.0, 1)
        ct.line_to(1, 1)
        ct.close_path()
        ct.stroke()

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
            self.texture.set_surface_size(
                int(new_w), self.texture.get_property('surface_height'))
            self.texture.invalidate()

    def create_obj(self):
        if self.obj_id is None:
            self.create(self.proc_type, str(self.value))
        if self.obj_id is None:
            print "MessageElement: could not create message obj"
        else:
            MFPGUI().mfp.set_do_onload(self.obj_id, True)
            self.obj_state = self.OBJ_COMPLETE

        self.draw_ports()
        self.texture.invalidate()

    def move(self, x, y):
        self.position_x = x
        self.position_y = y
        self.set_position(x, y)

        for c in self.connections_out:
            c.draw()

        for c in self.connections_in:
            c.draw()

    def set_bounds(self, lower, upper):
        self.min_value = lower
        self.max_value = upper 

        if ((self.value < self.min_value) or (self.value > self.max_value)):
            self.update_value(self.value)
        self.send_params()

    def update_value(self, value):
        if self.min_value is not None and value < self.min_value:
            value = self.min_value 

        if self.max_value is not None and value > self.max_value:
            value = self.max_value 

        # called by enumcontrolmode
        str_rep = self.format_value(value)
        self.label.set_text(str_rep)
        self.value = float(str_rep)

        if self.obj_id is None:
            self.create_obj()
        if self.obj_id is not None:
            MFPGUI().mfp.send(self.obj_id, 0, self.value)

    def update(self):
        self.label.set_text(self.format_value(self.value))
        self.texture.invalidate()

    def label_edit_start(self):
        pass

    def label_edit_finish(self, *args):
        # called by labeleditmode
        t = self.label.get_text()
        self.update_value(float(t))
        if self.obj_id is None:
            self.create_obj()
        MFPGUI().mfp.send(self.obj_id, 0, self.value)

    def configure(self, params):
        fmt_changed = False
        val_changed = False

        v = params.get("value", float(self.obj_args or 0.0))
        if v != self.value:
            self.value = v
            val_changed = True

        v = params.get("scientific")
        if v:
            if not self.scientific:
                fmt_changed = True
            self.scientific = True
        else:
            if self.scientific:
                fmt_changed = True
            self.scientific = False

        v = params.get("digits")
        if v is not None and v != self.digits:
            self.digits = v
            fmt_changed = True

        if fmt_changed:
            self.format_update()
        if fmt_changed or val_changed:
            self.label.set_text(self.format_value(self.value))

        self.texture.invalidate()

        if 'width' in params:
            del params['width']
        if 'height' in params:
            del params['height']

        PatchElement.configure(self, params)

    def port_position(self, port_dir, port_num):
        # tweak the right input port display to be left of the slant
        if port_dir == PatchElement.PORT_IN and port_num == 1:
            default = PatchElement.port_position(self, port_dir, port_num)
            return (default[0] - self.PORT_TWEAK, default[1])
        else:
            return PatchElement.port_position(self, port_dir, port_num)

    def select(self):
        self.move_to_top()
        self.selected = True
        self.texture.invalidate()

    def unselect(self):
        self.selected = False
        self.texture.invalidate()

    def delete(self):
        for c in self.connections_out + self.connections_in:
            c.delete()
        PatchElement.delete(self)

    def make_edit_mode(self):
        return EnumEditMode(self.stage, self, self.label)

    def make_control_mode(self):
        return EnumControlMode(self.stage, self)

