#! /usr/bin/env python2.6
'''
p_sig.py:  Builtin constant signal

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp


class Sig(Processor):
    doc_tooltip_obj = "Emit a constant signal"
    doc_tooltip_inlet = ["Value to emit (default: initarg 0)"]
    doc_tooltip_outlet = ["Signal output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            value = initargs[0]
        else:
            value = 0

        self.dsp_outlets = [0]
        self.dsp_init("sig~")
        self.dsp_obj.setparam("value", value)

    def trigger(self):
        val = float(self.inlets[0])
        self.dsp_obj.setparam("value", val)


def register():
    MFPApp().register("sig~", Sig)
