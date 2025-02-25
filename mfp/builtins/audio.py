#! /usr/bin/env python
'''
audio.py:  Builtin AudioOut/AudioIn DSP objects

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit 

class AudioOut(Processor):
    doc_tooltip_obj = "Output to JACK port"
    doc_tooltip_inlet = [ "Signal input", "JACK output port number (default: initarg 0)" ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 2, 0, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)

        if len(initargs):
            self.channel = initargs[0]
        else:
            self.channel = 0

        self.hot_inlets = [0, 1]
        self.dsp_inlets = [0]

    async def setup(self):
        await self.dsp_init("out~", channel=self.channel)

    async def trigger(self):
        if self.inlets[1] is not Uninit:
            channel = int(self.inlets[1])
            await self.dsp_setparam("channel", channel)


class AudioIn(Processor):
    doc_tooltip_obj = "Input from JACK port"
    doc_tooltip_inlet = [ "JACK input port number (default: initarg 0)" ]
    doc_tooltip_outlet = [ "Signal output" ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)

        if len(initargs):
            self.channel = initargs[0]
        else:
            self.channel = 0

        self.dsp_outlets = [0]

    async def setup(self):
        await self.dsp_init("in~", channel=self.channel)

    async def trigger(self):
        self.channel = int(self.inlets[0])
        await self.dsp_setparam("channel", self.channel)


def register():
    MFPApp().register("in~", AudioIn)
    MFPApp().register("out~", AudioOut)
