
#! /usr/bin/env python2.6
'''
ampl.py:  Detector (peak/rms)

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from mfp.main import MFPApp
from mfp import log


class Ampl(Processor):
    doc_tooltip_obj = "Compute RMS and peak amplitude"
    doc_tooltip_inlet = [ "Input signal" ]
    doc_tooltip_outlet = [ "RMS amplitude", "Peak amplitude" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 2, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        self.dsp_inlets = [0]
        self.dsp_outlets = [0, 1]
        self.dsp_init("ampl~")

    def trigger(self):
        if isinstance(self.inlets[0], dict):
            for param, val in self.inlets[0].items():
                try:
                    self.dsp_setparam(param, float(val))
                except Exception, e:
                    log.debug("ampl~: Error setting param", param, "to", type(val), str(val))
                    log.debug("ampl~: Exception:", str(e))


def register():
    MFPApp().register("ampl~", Ampl)
