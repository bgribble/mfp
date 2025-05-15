#! /usr/bin/env python
'''
hold.py: Track-and-hold

Copyright (c) 2020 Bill Gribble <grib@billgribble.com>
'''
from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit


class TrackHold(Processor):
    doc_tooltip_obj = "Track and hold"
    doc_tooltip_inlet = ["Signal input", "Hold signal"]
    doc_tooltip_outlet = ["Signal output", "Sample output"]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 2, 2, init_type, init_args, patch, scope, name, defs)

        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)
        self.hot_inlets = [0, 1]
        self.dsp_inlets = [0, 1]
        self.dsp_outlets = [0]
        self.init_response = "response" in kwargs and kwargs["response"]

    async def setup(self, **kwargs):
        if self.init_response:
            await self.dsp_init("hold~", track=True, response=True)
        else:
            await self.dsp_init("hold~", track=True)

    async def trigger(self):
        if self.inlets[0] is not Uninit:
            val = float(self.inlets[0])
            await self.dsp_obj.setparam("_sig_0", val)
        if self.inlets[1] is not Uninit:
            val = float(self.inlets[1])
            self.inlets[1] = Uninit
            await self.dsp_obj.setparam("_sig_1", val)

    def dsp_response(self, resp_type, resp_value):
        self.outlets[1] = resp_value


class SampleHold(Processor):
    doc_tooltip_obj = "Sample and hold"
    doc_tooltip_inlet = ["Signal input", "Hold signal"]
    doc_tooltip_outlet = ["Signal output", "Sample output"]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 2, 2, init_type, init_args, patch, scope, name, defs)

        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)
        self.hot_inlets = [0, 1]
        self.dsp_inlets = [0, 1]
        self.dsp_outlets = [0]
        self.init_response = "response" in kwargs and kwargs["response"]

    async def setup(self, **kwargs):
        if self.init_response:
            await self.dsp_init("hold~", response=1.0)
        else:
            await self.dsp_init("hold~")

    async def trigger(self):
        if self.inlets[0] is not Uninit:
            val = float(self.inlets[0])
            await self.dsp_obj.setparam("_sig_0", val)
        if self.inlets[1] is not Uninit:
            val = float(self.inlets[1])
            self.inlets[1] = Uninit
            await self.dsp_obj.setparam("_sig_1", val)

    def dsp_response(self, resp_type, resp_value):
        self.outlets[1] = resp_value


def register():
    MFPApp().register("hold~", TrackHold)
    MFPApp().register("track~", TrackHold)
    MFPApp().register("sample~", SampleHold)
