#! /usr/bin/env python
'''
scopeplot.py
Specialization of XYPlot for displaying waveform data from
buffers

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter 
from .xyplot import XYPlot
from mfp import log
from posix_ipc import SharedMemory

import os 
import numpy 


class ScopePlot (XYPlot):
    FLOAT_SIZE = 4
    def __init__(self, width, height):
        self.orig_x = 0
        self.orig_y = 1
        self.buf_info = None
        self.shm_obj = None
        self.data = []
        
        XYPlot.__init__(self, width, height)

    def set_field_origin(self, orig_x, orig_y, redraw=False):
        self.orig_x = orig_x
        self.orig_y = orig_y
        if redraw: 
            self.plot.invalidate() 

    def create_plot(self): 
        self.plot = Clutter.CairoTexture.new(self.plot_w, self.plot_h)
        self.plot.connect("draw", self.draw_field_cb)
        self.plot.show()

    def draw_field_cb(self, texture, ctx, *rest):
        if not self.data:
            return 
        texture.clear()
        ctx.translate(-self.orig_x, -self.orig_y)
        ctx.set_source_rgba(0, 0, 255, 1.0)
        ctx.set_line_width(0.3)
        ctx.move_to(*self.pt2px((0, self.data[0][0])))

        for ptnum, pt in enumerate(self.data[0]):
            ctx.line_to(*self.pt2px((ptnum, pt)))
        ctx.stroke()

    def save_style(self):
        print "FIXME: ScopePlot.save_style()"
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
                slc = os.read(self.shm_obj.fd, self.buf_info.size * self.FLOAT_SIZE)
                self.data.append(list(numpy.fromstring(slc, dtype=numpy.float32)))
                self.set_bounds(0, -1, len(self.data[0]), 1)
        except Exception, e:
            log.debug("scopeplot: error grabbing data", e)
            return None

    def command(self, action, data):
        if action == "buffer":
            log.debug("scopeplot: got buffer info", data)
            self.buf_info = data
        elif action == "grab":
            self._grab()
            self.plot.clear()
            self.plot.invalidate()
        return True
