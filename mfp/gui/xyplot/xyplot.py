#! /usr/bin/env python
'''
xyplot.py
Clutter widget supporting scatter, line, and roll plots

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter
import math
from .quilt import Quilt
from .. import ticks
from ..colordb import ColorDB 

class XYPlot (Clutter.Group):
    '''
    XYPlot: parent class of plot elements (ScatterPlot, ScopePlot)
    '''

    MARGIN_LEFT = 30
    MARGIN_BOT = 30
    AXIS_PAD = 5
    TICK_SIZE = 50

    LINEAR = 0
    LOG_DECADE = 1
    LOG_OCTAVE = 2

    def __init__(self, width, height):
        Clutter.Group.__init__(self)

        self.width = width
        self.height = height

        self.style = {}

        # scaling params
        self.x_min = 0
        self.x_max = 6.28
        self.y_min = -1
        self.y_max = 1
        self.axis_font_size = 8

        # colors 
        self.color_fg = ColorDB().find("default_fg_unsel")
        self.color_bg = ColorDB().find("default_bg")
        self.color_axes = ColorDB().find_cairo("default_fg_unsel")

        # initialized by create() call
        self.border = None
        self.plot_border = None
        self.x_axis = None
        self.x_axis_mode = self.LINEAR 
        self.x_scale = 1.0

        self.y_axis = None
        self.y_axis_mode = self.LINEAR 
        self.y_scale = 1.0

        self.plot = None
        self.plot_w = 0
        self.plot_h = 0

        self.create()

    def create(self):
        self.border = Clutter.Rectangle()
        self.border.set_border_width(0)
        self.border.set_border_color(self.color_fg)
        self.border.set_color(self.color_bg)
        self.border.set_size(self.width, self.height)
        self.border.set_position(0, 0)
        self.add_actor(self.border)

        self.plot_w = self.width - self.MARGIN_LEFT
        self.plot_h = self.height - self.MARGIN_BOT
        self._recalc_x_scale()
        self._recalc_y_scale()

        self.x_axis = Quilt(self.plot_w, self.MARGIN_BOT)
        self.x_axis.set_position(self.MARGIN_LEFT, self.height - self.MARGIN_BOT)
        self.x_axis.set_viewport_origin(0, 0)
        self.add_actor(self.x_axis)

        self.y_axis = Quilt(self.MARGIN_LEFT, self.plot_h)
        self.y_axis.set_position(0, 0)
        self.y_axis.set_viewport_origin(0, -self.plot_h / 2.0)
        self.add_actor(self.y_axis)

        self.x_axis.set_render_cb(self.draw_xaxis_cb)
        self.y_axis.set_render_cb(self.draw_yaxis_cb)

        self.plot_border = Clutter.Rectangle()
        self.plot_border.set_border_width(0)
        self.plot_border.set_border_color(self.color_fg)
        self.plot_border.set_color(self.color_bg)
        self.plot_border.set_size(self.plot_w, self.plot_h)
        self.plot_border.set_position(self.MARGIN_LEFT, 0)
        self.add_actor(self.plot_border)

        self.create_plot()  
        self.plot.set_position(self.MARGIN_LEFT, 0)
        self.add_actor(self.plot)

    def create_plot(self): 
        self.plot = Quilt(self.plot_w, self.plot_h)
        self.plot.set_render_cb(self.draw_field_cb)
        self.plot.set_viewport_origin(0, -self.plot_h / 2.0)

    def set_size(self, width, height):
        self.width = width
        self.height = height

        self.border.set_size(self.width, self.height)
        self.plot_w = self.width - self.MARGIN_LEFT
        self.plot_h = self.height - self.MARGIN_BOT
        self.x_axis.set_size(self.plot_w, self.MARGIN_BOT)
        self.x_axis.set_position(self.MARGIN_LEFT, self.height - self.MARGIN_BOT)
        self.y_axis.set_size(self.MARGIN_LEFT, self.plot_h)
        self.plot_border.set_size(self.plot_w, self.plot_h)
        self.plot.set_size(self.plot_w, self.plot_h)

        self.x_axis.redraw()
        self.y_axis.redraw()
        self.plot.redraw()

    def _recalc_x_scale(self):
        if self.x_axis_mode == self.LINEAR:
            self.x_scale = float(self.plot_w) / (self.x_max - self.x_min)
        elif self.x_axis_mode in (self.LOG_DECADE, self.LOG_OCTAVE):
            if self.x_min <= 0.0:
                self.x_min = min(abs(self.x_max / 100.0), 0.1) 
            self.x_scale = float(self.plot_w) / (math.log(self.x_max / float(self.x_min)))

        if self.x_axis:
            self.x_axis.clear()

    def _recalc_y_scale(self):
        if self.y_axis_mode == self.LINEAR:
            self.y_scale = -1.0 * float(self.plot_h) / (self.y_max - self.y_min)
        elif self.y_axis_mode in (self.LOG_DECADE, self.LOG_OCTAVE):
            if self.y_min <= 0.0:
                self.y_min = min(abs(self.y_max / 100.0), 0.1) 
            self.y_scale = -1.0 * float(self.plot_h) / (math.log(self.y_max / float(self.y_min)))

        if self.y_axis:
            self.y_axis.clear()


    def set_bounds(self, x_min, y_min, x_max, y_max):
        if ((x_min is None or x_min == self.x_min)
            and (x_max is None or x_max == self.x_max)
            and (y_min is None or y_min == self.y_min)
                and (y_max is None or y_max == self.y_max)):
            return

        if x_min is None:
            if x_max is not None:
                x_min = self.x_min + (x_max - self.x_max)
            else:
                x_min = self.x_min
                x_max = self.x_max
        elif x_max is None:
            x_max = self.x_max + (x_min - self.x_min)

        if y_min is None:
            if y_max is not None:
                y_min = self.y_min + (y_max - self.y_max)
            else:
                y_min = self.y_min
                y_max = self.y_max
        elif y_max is None:
            y_max = self.y_max + (y_min - self.y_min)

        # if scale is changing, really need to redraw all
        need_x_flush = need_y_flush = False

        if ((x_max - x_min) != (self.x_max - self.x_min)):
            need_x_flush = True

        if ((y_max - y_min) != (self.y_max - self.y_min)):
            need_y_flush = True

        if ((x_min != self.x_min) or (x_max != self.x_max)):
            self.x_min = x_min
            self.x_max = x_max
            self._recalc_x_scale()

            origin = self.pt2px((x_min, y_min))
            self.x_axis.set_viewport_origin(origin[0], 0, need_x_flush)

        if ((y_min != self.y_min) or (y_max != self.y_max)):
            self.y_min = y_min
            self.y_max = y_max
            self._recalc_y_scale()
            origin = self.pt2px((x_min, y_max))

            self.y_axis.set_viewport_origin(0, origin[1], need_y_flush)

        origin = self.pt2px((x_min, y_max))
        if need_x_flush or need_y_flush:
            self.reindex()

        self.set_field_origin(origin[0], origin[1], need_x_flush or need_y_flush)

    def set_field_origin(self, x_orig, y_orig, redraw):
        pass 

    def reindex(self):
        pass 

    def pt2px(self, p):
        if self.x_axis_mode == self.LINEAR: 
            x_pix = p[0] * self.x_scale
        elif self.x_axis_mode in (self.LOG_DECADE, self.LOG_OCTAVE): 
            if p[0] > 0.0:
                x_pix = math.log(p[0] / float(self.x_min)) * self.x_scale 
            else: 
                return None 

        if self.y_axis_mode == self.LINEAR: 
            y_pix = p[1] * self.y_scale 
        elif self.y_axis_mode in (self.LOG_DECADE, self.LOG_OCTAVE): 
            if p[1] > 0.0: 
                y_pix = math.log(p[1] / float(self.y_min)) * self.y_scale
            else: 
                return None 

        return [x_pix, y_pix]

    def px2pt(self, p):
        if self.x_axis_mode == self.LINEAR:
            x_pt = p[0] / self.x_scale 
        elif self.x_axis_mode in (self.LOG_DECADE, self.LOG_OCTAVE):
            x_pt = math.exp(p[0] / self.x_scale) * self.x_min 

        if self.y_axis_mode == self.LINEAR: 
            y_pt = p[1] / self.y_scale 
        elif self.y_axis_mode in (self.LOG_DECADE, self.LOG_OCTAVE):
            y_pt = math.exp(p[1] / self.y_scale) * self.y_min 

        return [x_pt, y_pt ]

    def draw_xaxis_cb(self, texture, ctx, px_min, px_max):
        tickfuncs = { self.LINEAR: ticks.linear, self.LOG_DECADE: ticks.decade,
                      self.LOG_OCTAVE: ticks.octave }

        pt_min = self.px2pt(px_min)
        pt_max = self.px2pt(px_max)

        tick_pad = self.px2pt((self.TICK_SIZE, 0))[0]
        tick_min = pt_min[0] - 2 * tick_pad
        tick_max = pt_max[0] + tick_pad

        # X axis
        tick_gen = tickfuncs.get(self.x_axis_mode)
        xticks = tick_gen(self.x_min, self.x_max, self.plot_w / self.TICK_SIZE,
                          tick_min, tick_max)
        ctx.set_source_rgba(self.color_axes.red, self.color_axes.green,
                           self.color_axes.blue, self.color_axes.alpha)
        ctx.set_font_size(self.axis_font_size)

        # the axis line
        ctx.move_to(0, self.AXIS_PAD)
        ctx.line_to(texture.get_width(), self.AXIS_PAD)
        ctx.stroke()

        # ticks
        for tick in xticks:
            tick_px = self.pt2px((tick, self.y_min))
            if tick_px is None:
                continue 

            ctx.move_to(tick_px[0] - px_min[0], self.AXIS_PAD)
            ctx.line_to(tick_px[0] - px_min[0], 3 * self.AXIS_PAD)
            ctx.stroke()
            ctx.move_to(tick_px[0] - px_min[0], self.MARGIN_BOT - self.AXIS_PAD)
            ctx.show_text("%.5g" % tick)

    def draw_yaxis_cb(self, texture, ctx, px_min, px_max):
        tickfuncs = { self.LINEAR: ticks.linear, self.LOG_DECADE: ticks.decade,
                      self.LOG_OCTAVE: ticks.octave }
        pt_min = self.px2pt(px_min)
        pt_max = self.px2pt(px_max)

        tick_pad = abs(self.px2pt((0, self.TICK_SIZE))[1])
        tick_min = pt_max[1] - 2 * tick_pad
        tick_max = pt_min[1] + tick_pad

        # Y axis ticks
        tick_gen = tickfuncs.get(self.y_axis_mode)
        yticks = tick_gen(self.y_min, self.y_max, float(self.plot_h) / self.TICK_SIZE,
                           tick_min, tick_max)
        ctx.set_source_rgba(self.color_axes.red, self.color_axes.blue, 
                            self.color_axes.green, self.color_axes.alpha)
        ctx.set_font_size(self.axis_font_size)

        # the axis line
        ctx.move_to(self.MARGIN_LEFT - self.AXIS_PAD, 0)
        ctx.line_to(self.MARGIN_LEFT - self.AXIS_PAD, texture.get_height())
        ctx.stroke()

        # ticks
        for tick in yticks:
            tick_px = self.pt2px((self.x_min, tick))

            if tick_px is None:
                continue
            ctx.move_to(self.MARGIN_LEFT - self.AXIS_PAD, tick_px[1] - px_min[1])
            ctx.line_to(self.MARGIN_LEFT - 3 * self.AXIS_PAD, tick_px[1] - px_min[1])
            ctx.stroke()
            ctx.save()
            ctx.move_to(self.AXIS_PAD, tick_px[1] - px_min[1])
            ctx.rotate(math.pi / 2)
            ctx.show_text("%.5g" % tick)
            ctx.restore()

    def configure(self, params):
        pass 
