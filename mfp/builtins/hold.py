#! /usr/bin/env python
'''
hold.py: Track-and-hold

Copyright (c) 2020 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit 

class Hold(Processor):
    doc_tooltip_obj = "Track and hold"
    doc_tooltip_inlet = ["Signal input", "Hold signal"]
    doc_tooltip_outlet = ["Signal output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args)
        self.hot_inlets = [0, 1]
        self.dsp_inlets = [0, 1]
        self.dsp_outlets = [0]
        self.dsp_init("hold~")

    def trigger(self):
        if self.inlets[0] is not Uninit: 
            val = float(self.inlets[0])
            self.dsp_obj.setparam("_sig_0", val)
        if self.inlets[1] is not Uninit: 
            val = float(self.inlets[1])
            self.dsp_obj.setparam("_sig_1", val)

def register():
    MFPApp().register("hold~", Hold)

