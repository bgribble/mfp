#! /usr/bin/env python
'''
slew.py:  Builtin slew rate limiter

Copyright (c) 2014 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit


class Slew(Processor):
    doc_tooltip_obj = "Limit the slew rate of a signal"
    doc_tooltip_inlet = ["Signal input", "Rise rate limit (per mS)",
                         "Fall rate limit (per mS)"]
    doc_tooltip_outlet = ["Signal output"]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 3, 1, init_type, init_args, patch, scope, name, defs)

        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)
        if len(initargs) > 1:
            rise = initargs[0]
            fall = initargs[1]
        elif len(initargs):
            rise = fall = initargs[0]
        else:
            rise = fall = 10000

        self.hot_inlets = [0, 1, 2]
        self.dsp_inlets = [0]
        self.dsp_outlets = [0]
        self.init_rise = rise
        self.init_fall = fall

    async def setup(self, **kwargs):
        await self.dsp_init("slew~")
        await self.dsp_obj.setparam("rise", self.init_rise)
        await self.dsp_obj.setparam("fall", self.init_fall)

    async def trigger(self):
        if self.inlets[0] is not Uninit:
            val = float(self.inlets[0])
            await self.dsp_obj.setparam("_sig_0", val)
        if self.inlets[1] is not Uninit:
            val = float(self.inlets[1])
            await self.dsp_obj.setparam("rise", val)
        if self.inlets[2] is not Uninit:
            val = float(self.inlets[2])
            await self.dsp_obj.setparam("fall", val)


def register():
    MFPApp().register("slew~", Slew)
