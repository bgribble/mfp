#! /usr/bin/env python
'''
delay.py:  Builtin delay DSP object

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp


class DelaySig (Processor):
    doc_tooltip_obj = "Signal delay line"
    doc_tooltip_inlet = ["Input signal to delay",
                         "Delay (ms) (default: initarg 0)"]
    doc_tooltip_outlet = ["Signal output"]
    dsp_type = "del~"

    DEFAULT_BUFSIZE = 1000

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        if len(initargs):
            self.init_size = initargs[0]
        else:
            self.init_size = 0

        if len(initargs) > 1:
            self.init_bufsize = initargs[1]
        else:
            self.init_bufsize = max(self.init_size, self.DEFAULT_BUFSIZE)

        self.dsp_inlets = [0, 1]
        self.dsp_outlets = [0]

    async def setup(self):
        await self.dsp_init(self.dsp_type, bufsize=self.init_bufsize, _sig_1=self.init_size)

    async def trigger(self):
        if isinstance(self.inlets[0], dict):
            for k, v in self.inlets[0].items():
                await self.dsp_setparam(k, v)


class DelayBlkSig (DelaySig):
    doc_tooltip_obj = "Signal delay line (min of 1 buffer delay)"
    doc_tooltip_inlet = ["Input signal to delay",
                         "Delay (ms) (default: initarg 0)"]
    doc_tooltip_outlet = ["Signal output"]
    dsp_type = "delblk~"


def register():
    MFPApp().register("del~", DelaySig)
    MFPApp().register("delblk~", DelayBlkSig)
