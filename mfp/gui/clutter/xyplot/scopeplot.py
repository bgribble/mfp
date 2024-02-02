#! /usr/bin/env python
'''
scopeplot.py
Specialization of XYPlot for displaying waveform data from
buffers

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import os
import numpy
from gi.repository import Clutter
from posix_ipc import SharedMemory
from mfp import log
from mfp.utils import catchall
from .xyplot import XYPlot


class ScopePlot (XYPlot):

    FLOAT_SIZE = 4

    def __init__(self, element, width, height, samplerate):
        self.orig_x = 0
        self.orig_y = 1

        self.samplerate = samplerate
        self.buf_info = None
        self.shm_obj = None
        self.colors = [
            (0, 0, 1, 1), (0, 1, 0, 1), (0, 1, 1, 1), (1, 0, 1, 1),
            (1, 1, 0, 1), (1, 0, 0, 1)
        ]
        self.data = []
        self.data_start = 0
        self.data_end = -1
        self.draw_complete_cb = None

        XYPlot.__init__(self, element, width, height)

    def set_field_origin(self, orig_x, orig_y, redraw=False):
        self.orig_x = orig_x
        self.orig_y = orig_y
        if redraw:
            self.plot.invalidate()

    @catchall
    def create_plot(self):
        self.plot = Clutter.CairoTexture.new(self.plot_w, self.plot_h)
        self.plot.connect("draw", self.draw_field_cb)
        self.plot.show()
        self.plot.invalidate()

    def draw_curve_simple(self, ctx, curve):
        dataslice = self.data[curve][self.data_start:self.data_end]
        xbase = self.data_start * 1000.0 / self.samplerate
        xincr = 1000.0 / self.samplerate

        ctx.set_source_rgba(*self.colors[curve % len(self.colors)])
        ctx.set_line_width(0.5)

        ctx.move_to(*self.pt2px((xbase, dataslice[0])))
        for pt in dataslice:
            ctx.line_to(*self.pt2px((xbase, pt)))
            xbase += xincr
        ctx.stroke()

    def draw_curve_minmax(self, ctx, curve):
        dataslice = self.data[curve][self.data_start:self.data_end]
        xbase = self.data_start * 1000.0 / self.samplerate
        xincr = 1000.0 / self.samplerate
        dscale = 2*self.plot_w / float(len(dataslice))
        points = []
        ctx.set_source_rgba(*self.colors[curve % len(self.colors)])
        ctx.set_line_width(0.5)

        prevmin = 10000000
        prevmax = -10000000
        pmin = None
        pmax = None
        ptindex = 0
        ptpos = 0

        for pt in dataslice:
            if pmin is None or pt < pmin:
                pmin = pt
            if pmax is None or pt > pmax:
                pmax = pt
            ptpos += dscale
            xbase += xincr
            if int(ptpos) > ptindex:
                if ((pmin > prevmin) and (pmin > prevmax)):
                    pmin = prevmax
                elif ((pmax < prevmin) and (pmax < prevmax)):
                    pmax = prevmin
                points.append((xbase, pmin, pmax))
                ptindex = int(ptpos)
                prevmin = pmin
                prevmax = pmax
                pmin = None
                pmax = None

        for x, ymin, ymax in points:
            pmin = self.pt2px((x, ymin))
            pmax = self.pt2px((x, ymax))

            if abs(pmin[1] - pmax[1]) < 0.25:
                delta = 0.4 - abs(pmin[1] - pmax[1])
                if pmin[1] < pmax[1]:
                    delta *= -1.0
                pmin[1] += delta/2.0
                pmax[1] -= delta/2.0
            ctx.move_to(*pmin)
            ctx.line_to(*pmax)
        ctx.stroke()

    @catchall
    def draw_field_cb(self, texture, ctx, *rest):
        if not self.data:
            return

        texture.clear()
        ctx.translate(-self.orig_x, -self.orig_y)
        for curve in range(len(self.data)):
            if len(self.data[curve]) > 2*self.plot_w:
                self.draw_curve_minmax(ctx, curve)
            else:
                self.draw_curve_simple(ctx, curve)
        if self.draw_complete_cb is not None:
            self.draw_complete_cb()

    def save_style(self):
        return {}

    def _grab(self):
        def offset(channel):
            return channel * self.buf_info.size * self.FLOAT_SIZE

        if self.buf_info is None:
            return None
        if self.shm_obj is None:
            self.shm_obj = SharedMemory(self.buf_info.buf_id)

        self.data = []
        try:
            for c in range(self.buf_info.channels):
                os.lseek(self.shm_obj.fd, offset(c), os.SEEK_SET)
                slc = os.read(self.shm_obj.fd, int(self.buf_info.size * self.FLOAT_SIZE))
                self.data.append(list(numpy.fromstring(slc, dtype=numpy.float32)))
                self.set_bounds(0, None, len(self.data[0])*1000/self.samplerate, None)
        except Exception as e:
            log.debug("scopeplot: error grabbing data", e)
            import traceback
            traceback.print_exc()
            return None

    def command(self, action, data):
        if action == "buffer":
            self.buf_info = data
            self.shm_obj = None
            self.plot.invalidate()
        elif action == "grab":
            self._grab()
            self.plot.invalidate()
        return True
