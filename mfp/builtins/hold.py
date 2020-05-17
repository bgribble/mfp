#! /usr/bin/env python
'''
hold.py: Track-and-hold

Copyright (c) 2020 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit 

class TrackHold(Processor):
    doc_tooltip_obj = "Track and hold"
    doc_tooltip_inlet = ["Signal input", "Hold signal"]
    doc_tooltip_outlet = ["Signal output", "Sample output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 2, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args)
        self.hot_inlets = [0, 1]
        self.dsp_inlets = [0, 1]
        self.dsp_outlets = [0]
        if "response" in kwargs:
            self.dsp_init("hold~", track=True, response=True)
        else:
            self.dsp_init("hold~", track=True)

    def trigger(self):
        if self.inlets[0] is not Uninit: 
            val = float(self.inlets[0])
            self.dsp_obj.setparam("_sig_0", val)
        if self.inlets[1] is not Uninit: 
            val = float(self.inlets[1])
            self.inlets[1] = Uninit
            self.dsp_obj.setparam("_sig_1", val)
        
    def dsp_response(self, resp_type, resp_value):
        self.outlets[1] = resp_value

class SampleHold(Processor):
    doc_tooltip_obj = "Sample and hold"
    doc_tooltip_inlet = ["Signal input", "Hold signal"]
    doc_tooltip_outlet = ["Signal output", "Sample output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 2, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args)
        self.hot_inlets = [0, 1]
        self.dsp_inlets = [0, 1]
        self.dsp_outlets = [0]

        if "response" in kwargs:
            self.dsp_init("hold~", response=True)
        else:
            self.dsp_init("hold~")

    def trigger(self):
        if self.inlets[0] is not Uninit: 
            val = float(self.inlets[0])
            self.dsp_obj.setparam("_sig_0", val)
        if self.inlets[1] is not Uninit: 
            val = float(self.inlets[1])
            self.inlets[1] = Uninit
            self.dsp_obj.setparam("_sig_1", val)
        
    def dsp_response(self, resp_type, resp_value):
        self.outlets[1] = resp_value

def register():
    MFPApp().register("hold~", TrackHold)
    MFPApp().register("track~", TrackHold)
    MFPApp().register("sample~", SampleHold)

