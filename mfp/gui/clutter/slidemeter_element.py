"""
clutter/slidemeter_element.py -- backend for fader and dial slider/meter types
"""

import math

from gi.repository import Clutter
import cairo

from mfp.utils import catchall
from ..colordb import ColorDB
from .base_element import ClutterBaseElementBackend
from ..slidemeter_element import (
    FaderElement,
    FaderElementImpl,
    BarMeterElement,
    BarMeterElementImpl,
    DialElement,
    DialElementImpl,
    SlideMeterElement,
)


class ClutterSlideMeterElementImpl(SlideMeterElement, ClutterBaseElementBackend):
    backend_name = "clutter"

    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        # create the texture if needed
        if not hasattr(self, 'texture') or not self.texture:
            self.texture = Clutter.Canvas.new()
            self.texture.connect("draw", self.draw_cb)
            self.group.set_content(self.texture)
            self.group.set_reactive(True)

            self.width = self.DEFAULT_W
            self.height = self.DEFAULT_H
            self.texture.set_size(self.width, self.height)
            self.group.set_size(self.width, self.height)

        self.group.set_position(x, y)

    def redraw(self):
        self.texture.invalidate()

    async def set_size(self, width, height):
        await super().set_size(width, height)
        self.texture.set_size(width, height)
        self.texture.invalidate()

    @catchall
    def draw_cb(self, texture, ct, width, height):
        c = ColorDB().normalize(self.get_color('stroke-color'))
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        lw = 1

        if self.orientation == self.HORIZONTAL:
            h = width - lw
            w = height - lw
        else:
            w = width - lw
            h = height - lw

        y_max = h
        y_min = 0

        if not self.show_scale:
            x_min = 0
            x_max = w
        elif self.scale_position == self.LEFT:
            x_min = self.SCALE_SPACE
            x_max = w
        elif self.scale_position == self.RIGHT:
            x_min = 0
            x_max = w - self.SCALE_SPACE

        bar_h = y_max - y_min
        bar_w = x_max - x_min

        # clear the drawing area
        ct.save()
        ct.set_operator(cairo.OPERATOR_CLEAR)
        ct.paint()
        ct.restore()

        # rotate if we are drawing horizontally
        if self.orientation == self.HORIZONTAL:
            self.hot_x_min = y_min
            self.hot_x_max = y_max
            self.hot_y_min = x_min
            self.hot_y_max = x_max
            ct.save()
            ct.rotate(math.pi / 2.0)
            ct.translate(lw/2, -h)
        else:
            self.hot_x_min = x_min
            self.hot_x_max = x_max
            self.hot_y_min = y_min
            self.hot_y_max = y_max
            ct.translate(lw/2, lw/2)

        # draw the scale if required
        if self.show_scale:
            fontsize = self.get_style('font-size-scale')
            c = ColorDB().normalize(self.get_color('text-color'))
            ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
            ct.set_font_size(fontsize)

            if self.scale_ticks is None:
                num_ticks = bar_h / self.TICK_SPACE
                self.scale_ticks = self.scale.ticks(num_ticks)

            for tick in self.scale_ticks:
                tick_y = y_max - bar_h*self.scale.fraction(tick)
                if self.scale_position == self.LEFT:
                    tick_x = x_min
                    txt_x = 5
                else:
                    tick_x = x_max + self.TICK_LEN
                    txt_x = x_max + self.TICK_LEN + 5

                ct.move_to(tick_x - self.TICK_LEN, tick_y)
                ct.line_to(tick_x, tick_y)
                ct.stroke()

                txt_y = fontsize + (tick_y / bar_h)*(bar_h - fontsize)
                ct.move_to(txt_x, txt_y)
                ct.show_text("%.3g" % tick)

        def val2pixels(val):
            scale_fraction = self.scale.fraction(val)
            return scale_fraction*bar_h

        # box
        ct.rectangle(x_min, y_min, bar_w, bar_h)
        ct.stroke()

        # filling
        min_fillval, max_fillval = self.fill_interval()

        h = val2pixels(max_fillval) - val2pixels(min_fillval)
        if self.zeropoint is not None and h < self.MIN_BARSIZE:
            h = self.MIN_BARSIZE

        c = ColorDB().normalize(self.get_color('meter-color'))
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        ct.rectangle(x_min+lw/2, y_max + lw/2 - val2pixels(max_fillval), bar_w-lw, h-lw)
        ct.fill()

        if self.orientation == self.HORIZONTAL:
            ct.restore()

    def point_in_slider(self, x, y):
        orig_x, orig_y = self.get_stage_position()
        x -= orig_x
        y -= orig_y
        return (
            self.hot_x_min <= x <= self.hot_x_max
            and self.hot_y_min <= y <= self.hot_y_max
        )

    def pixpos2value(self, x, y):
        orig_x, orig_y = self.get_stage_position()
        x -= orig_x
        y -= orig_y
        if self.orientation == self.VERTICAL:
            delta = self.hot_y_max - y
            total = self.hot_y_max - self.hot_y_min
        else:
            delta = x - self.hot_x_min
            total = self.hot_x_max - self.hot_x_min

        fraction = delta / float(total)
        return self.scale.value(fraction)

    def add_pixdelta(self, dx, dy):
        if self.orientation == self.VERTICAL:
            delta = dy / float(self.hot_y_max - self.hot_y_min)
        else:
            delta = dx / float(self.hot_x_max - self.hot_x_min)

        scalepos = self.scale.fraction(self.value) + delta
        return self.scale.value(scalepos)


class ClutterFaderElementImpl(
    FaderElement, FaderElementImpl, ClutterSlideMeterElementImpl
):
    backend_name = "clutter"


class ClutterBarMeterElementImpl(
    BarMeterElement, BarMeterElementImpl, ClutterSlideMeterElementImpl
):
    backend_name = "clutter"


class ClutterDialElementImpl(DialElement, DialElementImpl, ClutterSlideMeterElementImpl):
    backend_name = "clutter"

    def __init__(self, window, x, y):
        # create the texture
        self.texture = Clutter.Canvas.new()

        super().__init__(window, x, y)

        self.texture.connect("draw", self.draw_cb)
        self.group.set_content(self.texture)
        self.group.set_reactive(True)

        self.width = self.DEFAULT_W
        self.height = self.DEFAULT_H
        self.texture.set_size(self.width, self.height)
        self.group.set_size(self.width, self.height)
        self.redraw()

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
        orig_x, orig_y = self.get_stage_position()
        x -= orig_x
        y -= orig_y
        _, theta = self.r2p(x, y)
        if theta > self.THETA_MAX and theta < self.THETA_MIN:
            return False
        return True

    def pixpos2value(self, x, y):
        orig_x, orig_y = self.get_stage_position()
        x -= orig_x
        y -= orig_y
        _, theta = self.r2p(x, y)

        if theta > self.THETA_MAX and theta < self.THETA_MIN:
            return None
        if theta < self.THETA_MIN:
            theta += 2*math.pi

        theta -= self.THETA_MIN
        scale_fraction = theta / (2*math.pi-(self.THETA_MIN-self.THETA_MAX))
        return self.scale.value(scale_fraction)

    def add_pixdelta(self, dx, dy):
        delta = 0.01 * dy

        scalepos = self.scale.fraction(self.value) + delta
        return self.scale.value(scalepos)

    def val2theta(self, value):
        scale_fraction = self.scale.fraction(value)
        if scale_fraction > 1.0:
            scale_fraction = 1.0
        elif scale_fraction < 0:
            scale_fraction = 0
        theta = self.THETA_MIN + scale_fraction * (2*math.pi-(self.THETA_MIN-self.THETA_MAX))
        return theta

    @catchall
    def draw_cb(self, texture, ct, width, height):
        c = ColorDB().normalize(self.get_color('stroke-color'))
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        ct.set_line_width(1.0)

        # clear the drawing area
        ct.save()
        ct.set_operator(cairo.OPERATOR_CLEAR)
        ct.paint()
        ct.restore()

        # draw the scale if required
        if self.show_scale:
            ct.set_font_size(self.scale_font_size)

            if self.scale_ticks is None:
                num_ticks = int(self.dial_radius / 10)
                if not num_ticks % 2:
                    num_ticks += 1
                self.scale_ticks = self.scale.ticks(num_ticks)

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
        c = ColorDB().normalize(self.get_color('meter-color'))
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
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
