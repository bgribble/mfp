#! /usr/bin/env python
'''
delay.py:  Builtin delay DSP object

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp
from .. import Bang, Uninit
from mfp import log


class DelaySig (Processor):
    doc_tooltip_obj = "Signal delay line"
    doc_tooltip_inlet = ["Input signal to delay",
                         "Delay (ms) (default: initarg 0)"]
    doc_tooltip_outlet = ["Signal output" ]
    dsp_type = "del~"

    DEFAULT_BUFSIZE=1000

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        if len(initargs):
            size = initargs[0] 
        else: 
            size = 0

        if len(initargs) > 1:
            bufsize = initargs[1]
        else:
            bufsize = max(size, self.DEFAULT_BUFSIZE)

        self.dsp_inlets = [0, 1]
        self.dsp_outlets = [0]
        self.dsp_init(self.dsp_type, bufsize=bufsize, _sig_1=size)

    def trigger(self):
        if isinstance(self.inlets[0], dict):
            for k, v in self.inlets[0].items():
                self.dsp_setparam(k, v)

class DelayBlkSig (DelaySig):
    doc_tooltip_obj = "Signal delay line (min of 1 buffer delay)"
    doc_tooltip_inlet = ["Input signal to delay",
                         "Delay (ms) (default: initarg 0)"]
    doc_tooltip_outlet = ["Signal output" ]
    dsp_type = "delblk~"

def register():
    MFPApp().register("del~", DelaySig)
    MFPApp().register("delblk~", DelayBlkSig)
