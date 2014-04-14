#! /usr/bin/env python2.6
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

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 3, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        freq = 0
        ampl = 1.0 

        if len(initargs) > 0:
            freq = initargs[0]
        if len(initargs) > 1:
            ampl = initargs[1]

        self.dsp_inlets = [1, 2]
        self.dsp_outlets = [0]
        self.dsp_init("osc~", _sig_1=float(freq), _sig_2=float(ampl))

    def trigger(self):
        # number inputs to the DSP ins (freq, amp) are
        # handled automatically
        if self.inlets[0] is Bang:
            self.dsp_setparam("phase", float(0))
        else:
            phase = float(self.inlets[0])
            self.dsp_setparam("phase", phase)


def register():
    MFPApp().register("osc~", Osc)
