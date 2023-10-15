#! /usr/bin/env python
'''
vcfreq.py: Convert frequency to V/oct signal

Copyright (c) 2020 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit


class VCFreq(Processor):
    doc_tooltip_obj = "Convert frequency (Hz) to V/oct signal"
    doc_tooltip_inlet = ["Signal input", "Reference frequency (A4, default=440)"]
    doc_tooltip_outlet = ["Signal output"]

    A4_C0_RATIO = 26.908692
    DEFAULT_C0 = 16.35159375

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            self.base_freq = float(initargs[0])/self.A4_C0_RATIO
        else:
            self.base_freq = self.DEFAULT_C0
        self.hot_inlets = [0, 1]
        self.dsp_inlets = [0]
        self.dsp_outlets = [0]

    async def setup(self):
        await self.dsp_init("vcfreq~", base_freq=self.base_freq)

    async def trigger(self):
        if self.inlets[0] is not Uninit:
            val = float(self.inlets[0])
            await self.dsp_obj.setparam("_sig_0", val)
        if self.inlets[1] is not Uninit:
            val = float(self.inlets[1])/self.A4_C0_RATIO
            await self.dsp_obj.setparam("base_freq", val)


def register():
    MFPApp().register("vcfreq~", VCFreq)
