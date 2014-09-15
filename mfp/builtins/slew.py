#! /usr/bin/env python
'''
slew.py:  Builtin slew rate limiter 

Copyright (c) 2014 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp


class Slew(Processor):
    doc_tooltip_obj = "Limit the slew rate of a signal"
    doc_tooltip_inlet = ["Signal input", "Rise rate limit (per mS)", 
                         "Fall rate limit (per mS)" ]
    doc_tooltip_outlet = ["Signal output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 3, 1, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args)
        if len(initargs) > 1:
            rise = initargs[0]
            fall = initargs[1]
        elif len(initargs):
            rise = fall = initargs[0]
        else:
            rise = fall = 10000

        self.dsp_inlets = [0]
        self.dsp_outlets = [0]
        self.dsp_init("slew~")
        self.dsp_obj.setparam("rise", rise)
        self.dsp_obj.setparam("fall", fall)

    def trigger(self):
        val = float(self.inlets[0])
        self.dsp_obj.setparam("value", val)


def register():
    MFPApp().register("slew~", Slew)

