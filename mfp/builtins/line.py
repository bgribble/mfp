#! /usr/bin/env python
'''
p_line.py:  Builtin line/ramp generator

Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp


class Line(Processor):
    doc_tooltip_obj = "Ramp/line generator"
    doc_tooltip_inlet = ["Line segments input/set position"]
    doc_tooltip_outlet = ["Signal output"]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)

        self.init_segments = []
        if len(initargs):
            self.init_segments = self.convert_segments(initargs[0])

        self.dsp_outlets = [0]

    async def setup(self, **kwargs):
        await self.dsp_init("line~", segments=self.init_segments)

    async def trigger(self):
        if self.inlets[0] is not None:
            if isinstance(self.inlets[0], (float, int)):
                pos = float(self.inlets[0])
                await self.dsp_obj.setparam("position", pos)
            else:
                segs = self.convert_segments(self.inlets[0])
                await self.dsp_obj.setparam("segments", segs)

    def convert_segments(self, segments):
        if (
            isinstance(segments, (list, tuple))
            and not isinstance(segments[0], (list, tuple))
        ):
            # one-segment message
            segments = [segments]

        unpacked = []
        for s in segments:
            if isinstance(s, (float, int)):
                unpacked.extend([float(0.0), float(s), float(0.0)])
            elif len(s) == 3:
                unpacked.extend([float(s[0]), float(s[1]), float(s[2])])
            elif len(s) == 2:
                unpacked.extend([float(0.0), float(s[0]), float(s[1])])

        return unpacked


def register():
    MFPApp().register("line~", Line)
