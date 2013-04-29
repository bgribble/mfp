#! /usr/bin/env python
'''
slidemeter_element.py
A patch element corresponding to a vertical or horizontal slider/meter

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter
import math
from .patch_element import PatchElement
from .colordb import ColorDB
from .modes.slider import SliderEditMode, SliderControlMode, DialEditMode, DialControlMode
from mfp import MFPGUI
from . import ticks


class SlideMeterElement (PatchElement):
    '''
    Vertical/horizontal slider/meter element
    Contains an optional scale
    Can be output-only or interactive
    Scale can be dB or linear
    '''

    display_type = "slidemeter"
    proc_type = "slidemeter"

    DEFAULT_W = 25
    DEFAULT_H = 100
    SCALE_SPACE = 30
    TICK_SPACE = 14
    TICK_LEN = 5
    MIN_BARSIZE = 2.0

    VERTICAL = 0x00
    HORIZONTAL = 0x01 
    LINEAR = 0x00
    LOG = 0x01 
    LEFT = 0x00
    RIGHT = 0x01

    def __init__(self, window, x, y):
        PatchElement.__init__(self, window, x, y)
        self.param_list.extend(['min_value', 'max_value', 'show_scale', 'scale_type',
                                'scale_position', 'orientation', 'zeropoint'])
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
        self.zeropoint = None 

        # value to emit when at bottom of scale, useful for dB scales
        self.slider_zero = None

        # coordinates of "hot" (meter display) area, where
        # dragging works
        self.hot_x_min = None
        self.hot_x_max = None
        self.hot_y_min = None
        self.hot_y_max = None

        # create the texture
        self.texture = Clutter.CairoTexture.new(self.DEFAULT_W, self.DEFAULT_H)

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
        c = ColorDB.to_cairo(self.color_fg)
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)

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

        def val2pixels(val):
            scale_fraction = abs((val - self.min_value) / (self.max_value - self.min_value))
            return scale_fraction*bar_h 

        # box 
        ct.rectangle(x_min, y_min, bar_w, bar_h)
        ct.stroke()

        # filling 
        min_fillval, max_fillval = self.fill_interval() 

        h = val2pixels(max_fillval) - val2pixels(min_fillval)
        if self.zeropoint is not None and h < self.MIN_BARSIZE:
            h = self.MIN_BARSIZE 

        ct.rectangle(x_min, y_max - val2pixels(max_fillval), bar_w, h)
        ct.fill()

        if self.orientation == self.HORIZONTAL:
            ct.restore()


    def fill_interval(self): 
        if self.zeropoint is None:
            return (self.min_value, self.value)
        else:
            if self.value > self.zeropoint: 
                pmin = self.zeropoint
                pmax = self.value 
            else: 
                pmin = self.value 
                pmax = self.zeropoint 
            return (pmin, pmax)

    def point_in_slider(self, x, y):
        orig_x, orig_y = self.get_stage_position()
        x -= orig_x
        y -= orig_y
        if (self.hot_x_min <= x <= self.hot_x_max
            and self.hot_y_min <= y <= self.hot_y_max):
            return True
        else:
            return False

    def pixpos2value(self, xpos, ypos):
        if self.orientation == self.VERTICAL:
            delta = self.hot_y_max - ypos    
            total = self.hot_y_max - self.hot_y_min
        else: 
            delta = xpos - self.hot_x_min
            total = self.hot_x_max - self.hot_x_min

        rv = (float(delta) / total) * (self.max_value - self.min_value)
        return rv

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

    def set_zeropoint(self, zp):
        self.zeropoint = zp
        self.update()
        self.send_params()

    def configure(self, params):
        changes = False

        v = params.get("orientation")
        if (v is not None and v in (1, "h", "horiz", "horizontal") 
            and not (self.orientation & self.HORIZONTAL)):
            self.set_orientation(self.HORIZONTAL)
            changes = True 
        elif (v is not None and v in (0, "v", "vert", "vertical") 
              and (self.orientation & self.HORIZONTAL)):
            self.set_orientation(self.VERTICAL)
            changes = True 

        v = params.get("zeropoint")
        if v != self.zeropoint: 
            self.zeropoint = v
            changes = True 

        v = params.get("scale")
        if (v == "linear" and self.scale_type != self.LINEAR): 
            self.scale_type = self.LINEAR
            changes = True 
        elif (v in ("log", "log10", "decade") and self.scale_type != self.LOG):
            self.scale_type = self.LOG
            changes = True 

        v = params.get("scale_position")
        if (v is not None and v in (1, "r", "R", "right") and self.scale_position != self.RIGHT): 
            self.scale_position = self.RIGHT 
            changes = True 
        elif (v is not None and v in (0, "l", "L", "left") and self.scale_position != self.LEFT):
            self.scale_position = self.LEFT 
            changes = True 
        
        for p in ("show_scale", "slider_enable", "min_value", "max_value", "scale_ticks"):
            v = params.get(p)
            if v is not None and hasattr(self, p):
                changes = True
                setattr(self, p, v)
                if p in ("min_value", "max_value"):
                    self.scale_ticks = None

        v = params.get("value")
        if v is not None:
            if v < self.min_value:
                v = self.min_value
            if v > self.max_value:
                v = self.max_value
            if self.value != v: 
                changes = True 
                self.value = v

        PatchElement.configure(self, params)
        if changes:
            self.texture.clear()
            self.texture.invalidate()

    def set_size(self, width, height):
        PatchElement.set_size(self, width, height)
        self.texture.set_size(width, height)
        self.texture.set_surface_size(width, height)
        self.texture.invalidate()

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

class DialElement(SlideMeterElement): 
    display_type = "dial" 
    proc_type = "slidemeter" 

    DEFAULT_W = 50 
    DEFAULT_H = 50 
    DEFAULT_R = 24
    BAR_WIDTH = 0.7
    THETA_MIN = 0.65*math.pi
    THETA_MAX = 0.35*math.pi 
    DRAG_SCALE = 0.01
    MIN_WEDGE = 0.1

    def __init__(self, window, x, y):
        self.dial_radius = self.DEFAULT_R 
        SlideMeterElement.__init__(self, window, x, y)

    def set_orientation(self, orientation):
        pass 

    def set_show_scale(self, show_scale):
        if show_scale == self.show_scale: 
            return 

        if show_scale:
            self.show_scale = True
            self.set_size(2*self.dial_radius + 2.0 + 7*self.scale_font_size, 
                          2*self.dial_radius + 2.0 + 3*self.scale_font_size)
        else:
            self.show_scale = False
            self.set_size(2*self.dial_radius + 2.0, 2*self.dial_radius + 2.0)

    def p2r(self, r, theta):
        x = (self.width / 2.0) + r * math.cos(theta)
        y = (self.height / 2.0) + r * math.sin(theta)
        return (x, y)

    def r2p(self, x, y):
        dx = x - self.width/2.0
        dy = y - self.height/2.0
        theta = math.atan2(dy, dx)
        r = (x*x + y*y)**0.5
        return (r, theta)

    def point_in_slider(self, x, y):
        r, theta = self.r2p(x, y)
        if theta > self.THETA_MAX and theta < self.THETA_MIN:
            return False 
        else: 
            return True 

    def pixpos2value(self, x, y):
        r, theta = self.r2p(x, y)
        if theta > self.THETA_MAX and theta < self.THETA_MIN:
            return None 
        elif theta < self.THETA_MIN:
            theta += 2*math.pi

        theta -= self.THETA_MIN
        scale_fraction = theta / (2*math.pi-(self.THETA_MIN-self.THETA_MAX))
        return self.min_value + scale_fraction * (self.max_value - self.min_value)
            
    def pixdelta2value(self, dx, dy): 
        return dy * self.DRAG_SCALE * (self.max_value - self.min_value)

    def val2theta(self, value):
        scale_fraction = abs((value - self.min_value) / (self.max_value - self.min_value))
        if scale_fraction > 1.0:
            scale_fraction = 1.0
        elif scale_fraction < 0:
            scale_fraction = 0
        theta = self.THETA_MIN + scale_fraction * (2*math.pi-(self.THETA_MIN-self.THETA_MAX))
        return theta

    def draw_cb(self, texture, ct): 
        c = ColorDB.to_cairo(self.color_fg)
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        ct.set_line_width(1.0)
        theta = self.val2theta(self.value)
        texture.clear()

        # draw the scale if required
        if self.show_scale:
            ct.set_font_size(self.scale_font_size)

            if self.scale_ticks is None:
                num_ticks = int(self.dial_radius / 10)
                if not num_ticks % 2:
                    num_ticks += 1
                self.scale_ticks = ticks.linear(self.min_value, self.max_value, num_ticks)

            for tick in self.scale_ticks:
                tick_theta = self.val2theta(tick)
                tick_x0, tick_y0 = self.p2r(self.dial_radius, tick_theta)
                tick_x1, tick_y1 = self.p2r(self.dial_radius + self.TICK_LEN, tick_theta)
                ct.move_to(tick_x0, tick_y0)
                ct.line_to(tick_x1, tick_y1)
                ct.stroke()
                
                txt_x, txt_y = self.p2r(self.dial_radius + self.TICK_LEN + 1, tick_theta)

                txt_x -= 2*self.scale_font_size * math.sin(tick_theta/2.0)
                txt_y += self.scale_font_size * (math.cos(tick_theta-math.pi/2.0)+1)/2.0
                ct.move_to(txt_x, txt_y)
                ct.show_text("%.3g" % tick)

        # Draw the outline of the dial 
        ct.move_to(*self.p2r(self.dial_radius, self.THETA_MIN))
        ct.arc(self.width/2.0, self.height/2.0, self.dial_radius, self.THETA_MIN, self.THETA_MAX)

        r = self.dial_radius * (1.0 - self.BAR_WIDTH)
        ct.line_to(*self.p2r(r, self.THETA_MAX))
        ct.arc_negative(self.width/2.0, self.height/2.0, r, self.THETA_MAX, self.THETA_MIN)
        ct.close_path()
        ct.stroke()

        # and the tasty filling 
        min_val, max_val = self.fill_interval()
        min_theta = self.val2theta(min_val)
        max_theta = self.val2theta(max_val)

        if self.zeropoint is not None and abs(max_theta - min_theta) < self.MIN_WEDGE:
            max_theta += self.MIN_WEDGE/2.0
            min_theta -= self.MIN_WEDGE/2.0

        ct.move_to(*self.p2r(self.dial_radius, min_theta))
        ct.arc(self.width/2.0, self.height/2.0, self.dial_radius, min_theta, max_theta)

        r = self.dial_radius * (1.0 - self.BAR_WIDTH)
        ct.line_to(*self.p2r(r, max_theta))
        ct.arc_negative(self.width/2.0, self.height/2.0, r, max_theta, min_theta)
        ct.close_path()
        ct.fill()

    def make_edit_mode(self):
        if self.obj_id is None:
            # create the underlying var
            self.create(self.proc_type, str(self.value))
            if self.obj_id is None:
                return None 
            else:
                self.draw_ports()
        return DialEditMode(self.stage, self, "Dial edit")

    def make_control_mode(self):
        return DialControlMode(self.stage, self, "Dial control")



