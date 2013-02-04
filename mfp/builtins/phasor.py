#! /usr/bin/env python2.6
'''
phasor.py:  Builtin phasor DSP object

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from mfp.main import MFPApp
from .. import Bang, Uninit
from mfp import log


class Phasor(Processor):
    doc_tooltip_obj = "Phasor (0-1 ramp) oscillator" 
    doc_tooltip_inlet = ["Phase reset (radians)",
                         "Frequency (hz) (default: initarg 0 or 0)"
                         "Amplitude (default: initarg 1 or 1)"]
    doc_tooltip_outlet = ["Signal output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 3, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            freq = initargs[0]
        else:
            freq = 0

        self.dsp_inlets = [1, 2]
        self.dsp_outlets = [0]
        self.dsp_init("phasor~", _sig_1=float(freq))

    def trigger(self):
        # number inputs to the DSP ins (freq, amp) are
        # handled automatically
        if self.inlets[0] is Bang:
            self.dsp_setparam("phase", float(0))
        else:
            try:
                phase = float(self.inlets[0])
                self.dsp_setparam("phase", phase)
            except Exception, e:
                log.debug("phasor~: Can't convert %s to a frequency value" % self.inlets[0])
                log.debug("phasor~: Exception:", e)


def register():
    MFPApp().register("phasor~", Phasor)
