#! /usr/bin/env python2.6
'''
del.py:  Builtin delay DSP object

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from mfp.main import MFPApp
from .. import Bang, Uninit
from mfp import log


class DelaySig (Processor):
    doc_tooltip_obj = "Signal delay line"
    doc_tooltip_inlet = ["Input signal to delay",
                         "Delay (ms) (default: initarg 0)"]
    doc_tooltip_outlet = ["Signal output" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        if len(initargs):
            size = initargs[0] 
        else: 
            size = 0

        self.dsp_inlets = [0, 1]
        self.dsp_outlets = [0]
        self.dsp_init("del~", bufsize=size, _sig_1=size)

    def trigger(self):
        if isinstance(self.inlets[0], dict):
            for k, v in self.inlets[0].items():
                self.dsp_setparam(k, v)

def register():
    MFPApp().register("del~", DelaySig)
