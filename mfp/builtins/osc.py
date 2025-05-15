#! /usr/bin/env python
'''
osc.py:  Builtin oscillator DSP objects

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp
from .. import Bang, Uninit
from mfp import log


class Osc(Processor):
    doc_tooltip_obj = "Sine oscillator"
    doc_tooltip_inlet = ["Phase reset (radians)",
                         "Frequency (hz) (min: 0, max: samplerate/2, default: initarg 0)",
                         "Amplitude (default: initarg 1)"]
    doc_tooltip_outlet = ["Signal output" ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 3, 1, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)
        self.init_freq = 0
        self.init_ampl = 1.0

        if len(initargs) > 0:
            self.init_freq = initargs[0]
        if len(initargs) > 1:
            self.init_ampl = initargs[1]

        self.dsp_inlets = [1, 2]
        self.dsp_outlets = [0]

    async def setup(self, **kwargs):
        await self.dsp_init("osc~", _sig_1=float(self.init_freq), _sig_2=float(self.init_ampl))

    async def trigger(self):
        # number inputs to the DSP ins (freq, amp) are
        # handled automatically
        if self.inlets[0] is Bang:
            await self.dsp_setparam("phase", float(0))
        else:
            phase = float(self.inlets[0])
            await self.dsp_setparam("phase", phase)


def register():
    MFPApp().register("osc~", Osc)
