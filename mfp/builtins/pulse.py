#! /usr/bin/env python
'''
pulse.py:  Builtin oscillator DSP objects

Copyright (c) 2018 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp
from .. import Bang, Uninit
from mfp import log


class Pulse(Processor):
    doc_tooltip_obj = "Pulse/square oscillator"
    doc_tooltip_inlet = ["Phase reset (radians)", 
                         "Frequency (hz) (min: 0, max: samplerate/2, default: initarg 0)", 
                         "Amplitude (default: initarg 1)",
                         "Pulse Width (default: initarg 2)"]
    doc_tooltip_outlet = ["Signal output" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 4, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        freq = 0
        ampl = 1.0 
        pw = 0.5
        loval = -1.0 
        hival = 1.0
        if init_type == 'gate~':
            loval = 0.0;

        if len(initargs) > 0:
            freq = initargs[0]
        if len(initargs) > 1:
            ampl = initargs[1]
        if len(initargs) > 2:
            pw = initargs[2]

        self.dsp_inlets = [1, 2, 3]
        self.dsp_outlets = [0]
        self.dsp_init("pulse~", 
                      _sig_1=float(freq), 
                      _sig_2=float(ampl),
                      _sig_3=float(pw),
                      hival=hival,
                      loval=loval
                     )

    def trigger(self):
        # number inputs to the DSP ins (freq, amp) are
        # handled automatically
        if self.inlets[0] is Bang:
            self.dsp_setparam("phase", float(0))
        else:
            phase = float(self.inlets[0])
            self.dsp_setparam("phase", phase)


def register():
    MFPApp().register("pulse~", Pulse)
    MFPApp().register("gate~", Pulse)
