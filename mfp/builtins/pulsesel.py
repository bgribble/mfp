#! /usr/bin/env python
'''
pulsesel.py: Select some pulses from a pulse train

Copyright (c) 2018 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp
from .. import Bang, Uninit


class PulseSel(Processor):
    doc_tooltip_obj = "Pulse train divider/selector"
    doc_tooltip_inlet = [
        "Signal input/reset",
        "Period",
        "Selection bitmask",
        "Trigger threshold (default: 0.25)",
    ]
    doc_tooltip_outlet = ["Signal output"]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 4, 1, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)
        self.init_period = 2
        self.init_bitmask = 1
        self.init_thresh = 0.25

        if len(initargs) > 0:
            self.init_period = initargs[0]
        if len(initargs) > 1:
            self.init_bitmask = initargs[1]
        if len(initargs) > 2:
            self.init_thresh = initargs[2]

        self.dsp_inlets = [0]
        self.hot_inlets = [0, 1, 2, 3]
        self.dsp_outlets = [0]

    async def setup(self, **kwargs):
        await self.dsp_init(
            "pulsesel~",
            bitmask=self.init_bitmask, period=self.init_period, threshold=self.init_thresh
        )

    async def trigger(self):
        if self.inlets[0] is Bang:
            await self.dsp_setparam("phase", float(0))
        elif self.inlets[0] is not Uninit:
            await self.dsp_setparam("phase", self.inlets[0])

        if self.inlets[1] is not Uninit:
            await self.dsp_setparam("period", self.inlets[1])
            self.inlets[1] = Uninit

        if self.inlets[2] is not Uninit:
            await self.dsp_setparam("bitmask", self.inlets[2])
            self.inlets[2] = Uninit

        if self.inlets[3] is not Uninit:
            await self.dsp_setparam("threshold", self.inlets[3])
            self.inlets[3] = Uninit


def register():
    MFPApp().register("pulsesel~", PulseSel)
