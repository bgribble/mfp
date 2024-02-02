#! /usr/bin/env python
'''
builtins/stepseq.py:  Builtin step sequencer

Copyright (c) 2018-2019 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp


class StepSeq(Processor):
    doc_tooltip_obj = "Step sequencer (DSP)"
    doc_tooltip_inlet = ["Step values", "Clock"]
    doc_tooltip_outlet = ["Step value output", "Trigger output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 2, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        self.init_steps = []
        if len(initargs):
            self.init_steps = self.convert_steps(initargs[0])

        self.dsp_inlets = [1]
        self.dsp_outlets = [0, 1]

    async def setup(self):
        await self.dsp_init("stepseq~", steps=self.init_steps, trig_ms=10, threshold=0.5)

    async def trigger(self):
        if self.inlets[0] is not None:
            if isinstance(self.inlets[0], (float, int)):
                pos = float(self.inlets[0])
                await self.dsp_obj.setparam("position", pos)
            else:
                steps = self.convert_steps(self.inlets[0])
                await self.dsp_obj.setparam("steps", steps)

    # steps come in as a list of lists/tuples
    # each step is (value: float, trigger: bool, slur: float)
    # if a step is a singleton, it's just a value with trigger=True
    # and slur=0.  Else trigger defaults to True and slur to 0.
    def convert_steps(self, steps):
        if not isinstance(steps, (list, tuple)):
            # a single value sequence
            steps = [steps]

        unpacked = []
        for s in steps:
            if isinstance(s, (float, int)):
                unpacked.extend([float(s), float(1.0), float(0.0)])
            elif len(s) > 2:
                unpacked.extend([float(s[0]), float(s[1]), float(s[2])])
            elif len(s) == 2:
                unpacked.extend([float(s[0]), float(s[1]), float(0.0)])
            elif len(s) == 1:
                unpacked.extend([float(s[0]), float(1.0), float(0.0)])

        return unpacked


def register():
    MFPApp().register("stepseq~", StepSeq)
