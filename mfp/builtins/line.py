#! /usr/bin/env python2.6
'''
p_line.py:  Builtin line/ramp generator

Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from mfp.main import MFPApp


class Line(Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        segments = []
        if len(initargs):
            segments = self.convert_segments(initargs[0])

        self.dsp_outlets = [0]
        self.dsp_init("line~", segments=segments)

    def trigger(self):
        if self.inlets[0] is not None:
            if isinstance(self.inlets[0], (float, int)):
                pos = float(self.inlets[0])
                self.dsp_obj.setparam("position", pos)
            else: 
                try:
                    segs = self.convert_segments(self.inlets[0])
                    self.dsp_obj.setparam("segments", segs)
                except:
                    import traceback
                    traceback.print_exc()
                    print "Error processing arg for line~:", self.inlets[0]

    def convert_segments(self, segments):
        if (isinstance(segments, (list, tuple)) 
            and not isinstance(segments[0], (list, tuple))):
            # one-segment message 
            segments = [segments]

        try:
            unpacked = []
            for s in segments:
                if isinstance(s, (float, int)):
                    unpacked.extend([float(0.0), float(s), float(0.0)])
                elif len(s) == 3:
                    unpacked.extend([float(s[0]), float(s[1]), float(s[2])])
                elif len(s) == 2:
                    unpacked.extend([float(0.0), float(s[0]), float(s[1])])

            return unpacked
        except Exception, e:
            return []


def register():
    MFPApp().register("line~", Line)
