#! /usr/bin/env python
'''
enum_element.py
A patch element corresponding to a number box or enum selector

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter
import cairo
from .text_widget import TextWidget
from .base_element import BaseElement
from .colordb import ColorDB
from mfp.gui_main import MFPGUI
from .modes.enum_control import EnumEditMode, EnumControlMode


class EnumElement (BaseElement):
    display_type = "enum"
    proc_type = "enum"

    PORT_TWEAK = 7

    def __init__(self, window, x, y):
        BaseElement.__init__(self, window, x, y)

        self.value = 0
        self.digits = 1
        self.min_value = None
        self.max_value = None
        self.scientific = False
        self.format_str = "%.1f"
        self.connections_out = []
        self.connections_in = []
        self.update_required = True

        self.param_list.extend(['digits', 'min_value', 'max_value', 'scientific'])

        self.obj_state = self.OBJ_HALFCREATED

        # create elements
        self.texture = Clutter.Canvas.new()
        self.texture.connect("draw", self.draw_cb)
        self.group.set_content(self.texture)

        self.label = TextWidget.get_factory()(self)

        self.group.set_reactive(True)

        # configure label
        self.label.set_position(4, 1)
        self.label.set_font_name(self.get_fontspec())
        self.label.set_color(self.get_color('text-color'))
        self.label.signal_listen('text-changed', self.text_changed_cb)
        self.label.set_text(self.format_value(self.value))

        # click handler
        # self.actor.connect('button-press-event', self.button_press_cb)

        self.move(x, y)
        self.set_size(35, 25)
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

    def draw_cb(self, texture, ct, width, height):
        lw = 2
        w = width - lw
        h = height - lw

        # clear the drawing area
        ct.save()
        ct.set_operator(cairo.OPERATOR_CLEAR)
        ct.paint()
        ct.restore()

        ct.set_line_width(lw)
        ct.set_antialias(cairo.ANTIALIAS_NONE)
        if self.obj_state == self.OBJ_COMPLETE:
            ct.set_dash([])
        else:
            ct.set_dash([8, 4])

        ct.translate(lw/2.0, lw/2.0)
        ct.move_to(0, 0)
        ct.line_to(0, h)
        ct.line_to(w, h)
        ct.line_to(w, h / 3.0)
        ct.line_to(w - h / 3.0, 0)
        ct.line_to(0, 0)
        ct.close_path()

        color = ColorDB().normalize(self.get_color('fill-color'))
        ct.set_source_rgba(color.red, color.green, color.blue, 1.0)
        ct.fill_preserve()

        color = ColorDB().normalize(self.get_color('stroke-color'))
        ct.set_source_rgba(color.red, color.green, color.blue, 1.0)
        ct.stroke()

    def set_size(self, w, h):
        BaseElement.set_size(self, w, h)

        self.texture.set_size(w, h)
        self.texture.invalidate()

    def text_changed_cb(self, *args):
        lwidth = self.label.get_property('width')
        bwidth = self.width

        new_w = None
        if (lwidth > (bwidth - 20)):
            new_w = lwidth + 20
        elif (bwidth > 35) and (lwidth < (bwidth - 20)):
            new_w = max(35, lwidth + 20)

        if new_w is not None:
            self.set_size(new_w, self.height)

    async def create_obj(self):
        if self.obj_id is None:
            self.create(self.proc_type, str(self.value))
        if self.obj_id is None:
            print("EnumElement: could not create var obj")
        else:
            await MFPGUI().mfp.set_do_onload(self.obj_id, True)
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

    async def set_bounds(self, lower, upper):
        self.min_value = lower
        self.max_value = upper

        if ((self.value < self.min_value) or (self.value > self.max_value)):
            await self.update_value(self.value)
        self.send_params()

    async def update_value(self, value):
        if self.min_value is not None and value < self.min_value:
            value = self.min_value

        if self.max_value is not None and value > self.max_value:
            value = self.max_value

        # called by enumcontrolmode
        str_rep = self.format_value(value)
        self.label.set_text(str_rep)
        self.value = float(str_rep)

        if self.obj_id is None:
            await self.create_obj()
        if self.obj_id is not None:
            await MFPGUI().mfp.send(self.obj_id, 0, self.value)

    def update(self):
        self.label.set_text(self.format_value(self.value))
        self.texture.invalidate()

    def label_edit_start(self):
        pass

    async def label_edit_finish(self, *args):
        # called by labeleditmode
        t = self.label.get_text()
        self.update_value(float(t))
        if self.obj_id is None:
            await self.create_obj()
        await MFPGUI().mfp.send(self.obj_id, 0, self.value)

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

        BaseElement.configure(self, params)

    def port_position(self, port_dir, port_num):
        # tweak the right input port display to be left of the slant
        if port_dir == BaseElement.PORT_IN and port_num == 1:
            default = BaseElement.port_position(self, port_dir, port_num)
            return (default[0] - self.PORT_TWEAK, default[1])
        else:
            return BaseElement.port_position(self, port_dir, port_num)

    def select(self):
        BaseElement.select(self)
        self.label.set_color(self.get_color('text-color'))
        self.texture.invalidate()

    def unselect(self):
        BaseElement.unselect(self)
        self.label.set_color(self.get_color('text-color'))
        self.texture.invalidate()

    async def make_edit_mode(self):
        return EnumEditMode(self.app_window, self, self.label)

    def make_control_mode(self):
        return EnumControlMode(self.app_window, self)
