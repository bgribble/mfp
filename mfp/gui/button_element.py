#! /usr/bin/env python2.6
'''
button_element.py
A patch element corresponding to a "bang" or "toggle" style button

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter
import cairo

from .patch_element import PatchElement
from .modes.clickable import ClickableControlMode
from ..gui_slave import MFPGUI
from ..bang import Bang


def rounded_box(ctx, xorig, yorig, w, h, rad):
    seg_h = h - 2 * rad
    seg_w = w - 2 * rad
    cdelta = rad / 2.0

    ctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
    ctx.translate(xorig, yorig)
    ctx.move_to(0, rad)
    ctx.line_to(0, rad + seg_h)
    ctx.curve_to(0, rad + seg_h + cdelta, cdelta, h, rad, h)
    ctx.line_to(rad + seg_w, h)
    ctx.curve_to(rad + seg_w + cdelta, h, w, h - rad + cdelta, w, h - rad)
    ctx.line_to(w, rad)
    ctx.curve_to(w, rad - cdelta, w - rad + cdelta, 0, w - rad, 0)
    ctx.line_to(rad, 0)
    ctx.curve_to(rad - cdelta, 0, 0, rad - cdelta, 0, rad)
    ctx.close_path()


class ButtonElement (PatchElement):
    porthole_height = 2
    porthole_width = 6
    porthole_minspace = 8
    porthole_border = 3
    proc_type = "var"

    PORT_TWEAK = 5

    def __init__(self, window, x, y):
        PatchElement.__init__(self, window, x, y)

        self.indicator = False

        # create elements
        self.texture = Clutter.CairoTexture.new(30, 30)
        self.texture.set_size(20, 20)
        self.texture.connect("draw", self.draw_cb)

        self.set_reactive(True)
        self.add_actor(self.texture)

        self.move(x, y)

        # request update when value changes
        self.update_required = True


    def draw_cb(self, texture, ct):
        w = self.texture.get_property('surface_width') - 2
        h = self.texture.get_property('surface_height') - 2

        c = None
        if self.selected:
            c = self.stage.color_selected
        else:
            c = self.stage.color_unselected
        texture.clear()
        ct.set_source_rgba(c.red, c.green, c.blue, 1.0)

        ct.set_line_width(1.5)
        ct.set_antialias(cairo.ANTIALIAS_NONE)

        # draw the box
        rounded_box(ct, 1, 1, w, h, 4)
        ct.stroke()

        # draw the indicator
        ioff = 5
        iw = w - 2 * ioff
        ih = h - 2 * ioff
        rounded_box(ct, ioff, ioff, iw, ih, 5)

        if self.indicator:
            ct.fill()
        else:
            ct.stroke()

    def configure(self, params):
        print "Button.configure:", params 
        if "value" in params:
            self.message = params.get("value")
            self.indicator = self.message 

        PatchElement.configure(self, params)
        self.texture.invalidate()

    def select(self):
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
        if self.obj_id is None:
            # create object
            self.create(self.proc_type, str(self.message))

            # complete drawing
            if self.obj_id is None:
                return None 
            else:
                self.draw_ports()
                self.texture.invalidate()

        return None 

    def make_control_mode(self):
        return ClickableControlMode(self.stage, self, "Button control")


class BangButtonElement (ButtonElement):
    display_type = "button"

    def __init__(self, window, x, y):
        self.message = Bang
        ButtonElement.__init__(self, window, x, y)

    def clicked(self):
        if self.obj_id is not None:
            if self.message is Bang:
                MFPGUI().mfp.send_bang(self.obj_id, 0)
            else:
                MFPGUI().mfp.send(self.obj_id, 0, self.message)
        self.indicator = True
        self.texture.invalidate()

        return False

    def unclicked(self):
        self.indicator = False
        self.texture.invalidate()

        return False

    def configure(self, params):
        if "value" in params:
            self.message = params.get("value")

        PatchElement.configure(self, params)
        self.texture.invalidate()


class ToggleButtonElement (ButtonElement):
    display_type = "toggle"

    def __init__(self, window, x, y):
        self.message = False 
        ButtonElement.__init__(self, window, x, y)

    def clicked(self):
        if self.message:
            self.message = False
            self.indicator = False 
        else:
            self.message = True
            self.indicator = True 

        if self.obj_id is not None:
            MFPGUI().mfp.send(self.obj_id, 0, self.message)
        self.texture.invalidate()
        return False

    def create(self, init_type, init_args):
        ButtonElement.create(self, init_type, init_args)
        if self.obj_id:
            MFPGUI().mfp.set_do_onload(self.obj_id, True)
        
    def unclicked(self):
        return False
