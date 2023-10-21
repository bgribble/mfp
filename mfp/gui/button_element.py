#! /usr/bin/env python
'''
button_element.py
A patch element corresponding to a "bang" or "toggle" style button

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter
import cairo

from mfp.utils import catchall
from .text_widget import TextWidget
from .patch_element import PatchElement
from .colordb import ColorDB
from .modes.clickable import ClickableControlMode
from .modes.label_edit import LabelEditMode
from ..gui_main import MFPGUI
from ..bang import Bang
import math


def circle(ctx, xorig, yorig, w, h):
    w = w-1.0
    h = h-1.0
    ctx.set_antialias(cairo.ANTIALIAS_DEFAULT)
    ctx.translate(xorig, yorig)
    ctx.arc(w/2.0, h/2.0, w/2.0, 0, 2*math.pi)
    ctx.close_path()


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
    proc_type = "var"

    style_defaults = {
        'porthole_height': 2,
        'porthole_width': 6,
        'porthole_minspace': 8,
        'porthole_border': 3,
        'fill-color:lit': 'default-alt-fill-color',
        'text-color:lit': 'default-light-text-color'
    }

    PORT_TWEAK = 5

    def __init__(self, window, x, y):
        PatchElement.__init__(self, window, x, y)

        self.indicator = False

        # create elements
        self.texture = Clutter.Canvas.new()
        self.texture.set_size(20, 20)
        self.set_content(self.texture)
        self.texture.connect("draw", self.draw_cb)

        self.label = TextWidget(self)
        self.label.set_color(self.get_color('text-color'))
        self.label.set_font_name(self.get_fontspec())
        self.label.connect('text-changed', self.label_changed_cb)
        self.label.set_reactive(False)
        self.label.set_use_markup(True)
        self.label_text = ''

        self.set_reactive(True)

        self.set_size(20, 20)
        self.move(x, y)

        self.param_list.append('label_text')
        # request update when value changes
        self.update_required = True

    def redraw(self):
        self.texture.invalidate()
        if self.indicator:
            self.label.set_color(self.get_color('text-color:lit'))
        else:
            self.label.set_color(self.get_color('text-color'))

    def center_label(self):
        label_halfwidth = self.label.get_property('width')/2.0
        label_halfheight = self.label.get_property('height')/2.0

        if label_halfwidth > 1:
            nwidth = max(self.width, 2*label_halfwidth + 10)
            nheight = max(self.height, 2*label_halfheight + 10)
            if nwidth != self.width or nheight != self.height:
                self.set_size(nwidth, nheight)

        if self.width and self.height:
            self.label.set_position(self.width/2.0-label_halfwidth,
                                    self.height/2.0-label_halfheight-2)

    @catchall
    def label_changed_cb(self, *args):
        self.center_label()

    def label_edit_start(self):
        return self.label_text

    async def label_edit_finish(self, widget, new_text, aborted=False):
        if not aborted:
            self.label_text = new_text
            self.send_params()
            if self.indicator:
                self.label.set_markup("<b>%s</b>" % self.label_text)
            else:
                self.label.set_markup(self.label_text)

            self.redraw()

    def set_size(self, width, height):
        PatchElement.set_size(self, width, height)
        self.texture.set_size(width, height)
        self.redraw()

    @catchall
    def draw_cb(self, texture, ct, width, height):
        w = width - 2
        h = height - 2

        c = ColorDB.to_cairo(self.get_color('stroke-color'))

        # Clear texture
        ct.save()
        ct.set_operator(cairo.OPERATOR_CLEAR)
        ct.paint()
        ct.restore()

        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)

        ct.set_line_width(1.5)
        ct.set_antialias(cairo.ANTIALIAS_NONE)

        # draw the box
        corner = max(2, 0.1*min(w, h))
        rounded_box(ct, 1, 1, w, h, corner)
        ct.stroke()

        # draw the indicator
        ioff = max(3, 0.075*min(w, h))
        iw = w - 2 * ioff
        ih = h - 2 * ioff
        rounded_box(ct, ioff, ioff, iw, ih, corner-1)

        c = ColorDB.to_cairo(self.get_color('fill-color:lit'))
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        if self.indicator:
            ct.fill()
        else:
            ct.stroke()

    def configure(self, params):
        set_text = False

        if "value" in params:
            self.message = params.get("value")
            self.indicator = self.message
            set_text = True

        if "label_text" in params:
            self.label_text = params.get("label_text", '')
            set_text = True

        if set_text:
            if self.indicator:
                self.label.set_markup("<b>%s</b>" % (self.label_text or ''))
            else:
                self.label.set_markup(self.label_text or '')
            self.center_label()

        PatchElement.configure(self, params)
        self.redraw()

    def select(self):
        PatchElement.select(self)
        self.redraw()

    def unselect(self):
        PatchElement.unselect(self)
        self.redraw()

    def make_edit_mode(self):
        if self.obj_id is None:
            # create object
            self.create(self.proc_type, str(self.indicator))

            # complete drawing
            if self.obj_id is None:
                return None
            else:
                self.draw_ports()
        self.redraw()

        return LabelEditMode(self.stage, self, self.label)

    def make_control_mode(self):
        return ClickableControlMode(self.stage, self, "Button control")


class BangButtonElement (ButtonElement):
    display_type = "button"

    def __init__(self, window, x, y):
        self.message = Bang

        ButtonElement.__init__(self, window, x, y)
        self.param_list.extend(['message'])

    def clicked(self):
        if self.obj_id is not None:
            if self.message is Bang:
                MFPGUI().async_task(MFPGUI().mfp.send_bang(self.obj_id, 0))
            else:
                MFPGUI().async_task(MFPGUI().mfp.send(self.obj_id, 0, self.message))
        self.indicator = True
        self.redraw()

        return False

    def unclicked(self):
        self.indicator = False
        self.redraw()

        return False

    def configure(self, params):
        if "message" in params:
            self.message = params.get("message")

        ButtonElement.configure(self, params)


class ToggleButtonElement (ButtonElement):
    display_type = "toggle"

    def __init__(self, window, x, y):
        self.off_message = False
        self.on_message = True
        ButtonElement.__init__(self, window, x, y)

        self.param_list.extend(['on_message', 'off_message'])

    def clicked(self):
        message = None
        if self.indicator:
            message = self.off_message
            self.indicator = False
        else:
            message = self.on_message
            self.indicator = True

        if self.obj_id is not None:
            MFPGUI().async_task(MFPGUI().mfp.send(self.obj_id, 0, message))
        self.redraw()
        return False

    def configure(self, params):
        if "on_message" in params:
            self.on_message = params.get("on_message")
        if "off_message" in params:
            self.off_message = params.get("off_message")
        ButtonElement.configure(self, params)

    def create(self, init_type, init_args):
        ButtonElement.create(self, init_type, init_args)
        if self.obj_id:
            MFPGUI().async_task(MFPGUI().mfp.set_do_onload.sync(self.obj_id, True))

    def unclicked(self):
        return False


class ToggleIndicatorElement (ButtonElement):
    display_type = "indicator"

    def make_control_mode(self):
        return PatchElement.make_control_mode(self)

    def select(self, *args):
        PatchElement.select(self)
        self.draw_ports()
        self.redraw()

    def unselect(self, *args):
        PatchElement.unselect(self)
        self.hide_ports()
        self.redraw()

    def draw_ports(self):
        if self.selected:
            PatchElement.draw_ports(self)

    @catchall
    def draw_cb(self, texture, ct, width, height):
        w = width - 2
        h = height - 2

        # clear texture
        ct.save()
        ct.set_operator(cairo.OPERATOR_CLEAR)
        ct.paint()
        ct.restore()

        c = ColorDB.to_cairo(self.get_color('stroke-color'))
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)

        ct.set_line_width(1.5)
        ct.set_antialias(cairo.ANTIALIAS_NONE)

        # draw the box
        circle(ct, 1, 1, w, h)
        ct.stroke()

        # draw the indicator
        ioff = max(3, 0.075*min(w, h))
        iw = w - 2 * ioff
        ih = h - 2 * ioff
        circle(ct, ioff, ioff, iw, ih)

        c = ColorDB.to_cairo(self.get_color('fill-color:lit'))
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        if self.indicator:
            ct.fill()
        else:
            ct.stroke()
