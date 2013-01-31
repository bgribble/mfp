#! /usr/bin/env python
'''
slidemeter_element.py
A patch element corresponding to a vertical or horizontal slider/meter

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter as clutter
import math
from patch_element import PatchElement
from .modes.slider import SliderEditMode, SliderControlMode
from mfp import MFPGUI
from mfp import log
from . import ticks


class SlideMeterElement (PatchElement):
    '''
    Vertical/horizontal slider/meter element
    Contains an optional scale
    Can be output-only or interactive
    Scale can be dB or linear
    '''

    display_type = "slidemeter"
    proc_type = "var"

    DEFAULT_W = 25
    DEFAULT_H = 100
    SCALE_SPACE = 30
    TICK_SPACE = 14
    TICK_LEN = 5

    VERTICAL = 0x00
    HORIZONTAL = 0x01 
    POSITIVE = 0x00
    NEGATIVE = 0x01
    LINEAR = 0x00
    LOG = 0x01 
    LEFT = 0x00
    RIGHT = 0x01

    def __init__(self, window, x, y):
        PatchElement.__init__(self, window, x, y)

        # parameters controlling display
        self.value = 0.0
        self.min_value = 0.0
        self.max_value = 1.0
        self.scale_ticks = None
        self.scale_font_size = 8
        self.show_scale = False
        self.slider_enable = True
        self.scale_type = self.LINEAR 
        self.scale_position = self.LEFT 
        self.orientation = self.VERTICAL
        self.direction = self.POSITIVE

        # value to emit when at bottom of scale, useful for dB scales
        self.slider_zero = None

        # coordinates of "hot" (meter display) area, where
        # dragging works
        self.hot_x_min = None
        self.hot_x_max = None
        self.hot_y_min = None
        self.hot_y_max = None

        # create the texture
        self.texture = clutter.CairoTexture.new(self.DEFAULT_W, self.DEFAULT_H)

        # configure
        self.add_actor(self.texture)
        self.texture.connect("draw", self.draw_cb)

        self.set_reactive(True)

        self.set_size(self.DEFAULT_W, self.DEFAULT_H)
        self.texture.invalidate()
        self.move(x, y)

        # request update when value changes
        self.update_required = True

    def draw_cb(self, texture, ct):
        c = None
        if self.selected:
            c = self.stage.color_selected
        else:
            c = self.stage.color_unselected
        ct.set_source_rgb(c.red, c.green, c.blue)

        if self.orientation == self.HORIZONTAL: 
            h = self.texture.get_property('surface_width') - 2
            w = self.texture.get_property('surface_height') - 2
        else: 
            w = self.texture.get_property('surface_width') - 2
            h = self.texture.get_property('surface_height') - 2

        y_max = h
        y_min = 1

        if not self.show_scale:
            x_min = 1 
            x_max = w
        elif self.scale_position == self.LEFT: 
            x_min = self.SCALE_SPACE
            x_max = w
        elif self.scale_position == self.RIGHT: 
            x_min = 1
            x_max = w - self.SCALE_SPACE 

        bar_h = y_max - y_min
        bar_w = x_max - x_min

        texture.clear()

        # rotate if we are drawing horizontally 
        if self.orientation == self.HORIZONTAL:
            self.hot_x_min = y_min 
            self.hot_x_max = y_max
            self.hot_y_min = x_min
            self.hot_y_max = x_max
            ct.save()
            ct.rotate(math.pi / 2.0)
            ct.translate(0, -h)
        else:
            self.hot_x_min = x_min 
            self.hot_x_max = x_max
            self.hot_y_min = y_min
            self.hot_y_max = y_max

        # draw the scale if required
        if self.show_scale:
            ct.set_font_size(self.scale_font_size)

            if self.scale_ticks is None:
                num_ticks = bar_h / self.TICK_SPACE
                if self.scale_type == self.LINEAR:
                    self.scale_ticks = ticks.linear(self.min_value, self.max_value, num_ticks)
                else: 
                    self.scale_ticks = ticks.decade(self.min_value, self.max_value, num_ticks)

            for tick in self.scale_ticks:
                tick_y = y_max - (bar_h*(tick - self.min_value)
                                           /(self.max_value-self.min_value))
                if self.scale_position == self.LEFT: 
                    tick_x = x_min
                    txt_x = 5
                else:
                    tick_x = x_max + self.TICK_LEN
                    txt_x = x_max + self.TICK_LEN + 5
                        
                ct.move_to(tick_x - self.TICK_LEN, tick_y)
                ct.line_to(tick_x, tick_y)
                ct.stroke()

                txt_y = self.scale_font_size + (tick_y / bar_h)*(bar_h - self.scale_font_size)
                ct.move_to(txt_x, txt_y)
                ct.show_text("%.3g" % tick)

        # draw the indicator and a surrounding box
        scale_fraction = abs((self.value - self.min_value) / (self.max_value - self.min_value))
        if self.direction ==  self.NEGATIVE: 
            bar_y_min = y_min
            scale_fraction = 1.0 - scale_fraction 
        else:
            bar_y_min = y_min + bar_h * (1.0 - scale_fraction)


        ct.rectangle(x_min, y_min, bar_w, bar_h)
        ct.stroke()
        ct.rectangle(x_min, bar_y_min, bar_w, bar_h * scale_fraction)
        ct.fill()
        if self.orientation == self.HORIZONTAL:
            ct.restore()

    def point_in_slider(self, x, y):
        orig_x, orig_y = self.get_position()
        x -= orig_x
        y -= orig_y
        if (self.hot_x_min <= x <= self.hot_x_max
                and self.hot_y_min <= y <= self.hot_y_max):
            return True
        else:
            return False

    def pixdelta2value(self, dx, dy):
        if self.orientation == self.VERTICAL:
            delta = dy 
            total = self.hot_y_max - self.hot_y_min
        else: 
            delta = -dx 
            total = self.hot_x_max - self.hot_x_min

        return (float(delta) / total) * (self.max_value - self.min_value)

    def update_value(self, value):
        if value >= self.max_value:
            value = self.max_value

        if value <= self.min_value:
            value = self.min_value

        if value != self.value:
            self.value = value
            self.texture.invalidate()
            MFPGUI().mfp.send(self.obj_id, 0, self.value)

    def update(self):
        self.texture.invalidate()

    def set_orientation(self, orient): 
        if orient != self.orientation:
            self.set_size(self.height, self.width)
        self.orientation = orient  

    def set_show_scale(self, show_scale):
        if show_scale == self.show_scale: 
            return 

        if show_scale:
            self.show_scale = True
            if self.orientation & self.HORIZONTAL:  
                self.set_size(self.get_width(), self.get_height() + self.SCALE_SPACE)
            else:
                self.set_size(self.get_width() + self.SCALE_SPACE, self.get_height())
        else:
            self.show_scale = False
            if self.orientation & self.HORIZONTAL:  
                self.set_size(self.get_width(), self.get_height() - self.SCALE_SPACE)
            else:
                self.set_size(self.get_width() - self.SCALE_SPACE, self.get_height())

    def set_bounds(self, min_val, max_val):
        self.max_value = max_val
        self.min_value = min_val
       
        newval = False 
        if self.value > self.max_value:
            self.value = self.max_value
            newval = True

        if self.value < self.min_value:
            self.value = self.min_value
            newval = True 

        if newval: 
            MFPGUI().mfp.send(self.obj_id, 0, self.value)

        self.scale_ticks = None 
        self.update()
        self.send_params()

    def configure(self, params):
        changes = False

        v = params.get("orientation")
        if (v and v in ("h", "horiz", "horizontal") 
            and not (self.orientation & self.HORIZONTAL)):
            self.set_orientation(self.HORIZONTAL)
            changes = True 
        elif (v and v in ("v", "vert", "vertical") 
              and (self.orientation & self.HORIZONTAL)):
            self.set_orientation(self.VERTICAL)
            changes = True 

        v = params.get("show_scale")

        v = params.get("direction")
        if (v in (1, "pos", "positive") and self.direction != self.POSITIVE): 
            self.direction = self.POSITIVE 
            changes = True 
        elif (v in (-1,  "neg", "negative") and self.direction != self.NEGATIVE):
            self.direction = self.NEGATIVE
            changes = True 

        v = params.get("scale")
        if (v == "linear" and self.scale_type != self.LINEAR): 
            self.scale_type = self.LINEAR
            changes = True 
        elif (v in ("log", "log10", "decade") and self.scale_type != self.LOG):
            self.scale_type = self.LOG
            changes = True 

        v = params.get("scale_pos")
        if (v in ("r", "R", "right") and self.scale_position != self.RIGHT): 
            self.scale_position = self.RIGHT 
            changes = True 
        elif (v in ("l", "L", "left") and self.scale_position != self.LEFT):
            self.scale_position = self.LEFT 
            changes = True 

        for p in ("value", "slider_enable", "min_value", "max_value", "scale_ticks"):
            v = params.get(p)
            if v is not None and hasattr(self, p):
                changes = True
                setattr(self, p, v)
                if p in ("min_value", "max_value"):
                    self.scale_ticks = None

        PatchElement.configure(self, params)
        if changes:
            self.texture.clear()
            self.texture.invalidate()

    def set_size(self, width, height):
        self.width = width
        self.height = height
        clutter.Group.set_size(self, self.width, self.height)
        self.texture.set_size(width, height)
        self.texture.set_surface_size(width, height)
        self.draw_ports()

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
        if self.obj_id is None:
            # create the underlying var
            self.create(self.proc_type, str(self.value))
            if self.obj_id is None:
                return None 
            else:
                self.draw_ports()
        return SliderEditMode(self.stage, self, "Fader/meter edit")

    def make_control_mode(self):
        return SliderControlMode(self.stage, self, "Fader/meter control")


class FaderElement(SlideMeterElement):
    pass


class BarMeterElement(SlideMeterElement):
    def __init__(self, window, x, y):
        SlideMeterElement.__init__(self, window, x, y)

        self.slider_enable = False
