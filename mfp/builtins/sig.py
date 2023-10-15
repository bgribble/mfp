#! /usr/bin/env python
'''
p_sig.py:  Builtin constant signal

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp


class Sig(Processor):
    doc_tooltip_obj = "Emit a constant signal"
    doc_tooltip_inlet = ["Value to emit (default: initarg 0)"]
    doc_tooltip_outlet = ["Signal output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            self.init_value = initargs[0]
        else:
            self.init_value = 0

        self.dsp_outlets = [0]

    async def setup(self):
        await self.dsp_init("sig~")
        await self.dsp_obj.setparam("value", self.init_value)

    async def trigger(self):
        val = float(self.inlets[0])
        await self.dsp_obj.setparam("value", val)


def register():
    MFPApp().register("sig~", Sig)
