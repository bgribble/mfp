#! /usr/bin/env python
'''
biquad.py: Biquad filter implementation

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp
from mfp import log
import math
from ..bang import Uninit

class Biquad(Processor):
    doc_tooltip_obj = "Biquad filter (5-parameter normalized form)"
    doc_tooltip_inlet = [ "Signal in or parameter dictionary with keys a1, a2, b0, b1, b2" ]
    doc_tooltip_outlet = [ "Signal out" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        self.dsp_inlets = [0]
        self.dsp_outlets = [0]

    async def setup(self):
        await self.dsp_init("biquad~")

    async def trigger(self):
        if isinstance(self.inlets[0], dict):
            for param, val in self.inlets[0].items():
                try:
                    await self.dsp_setparam(param, float(val))
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    log.debug("biquad~: Error setting param", param, "to", type(val), str(val))
                    log.debug("biquad~: Exception:", str(e))
                    self.error(tb)


def bq_hipass(freq, q):
    params = {}
    w0 = 2 * math.pi * freq / MFPApp().samplerate
    alpha = math.sin(w0) / (2*q)
    a0 = 1 + alpha
    params['a1'] = (-2.0*math.cos(w0)) / a0
    params['a2'] = (1 - alpha) / a0
    params['b0'] = (1 + math.cos(w0)) / (2.0 * a0)
    params['b1'] = -1.0*(1 + math.cos(w0)) / a0
    params['b2'] =  (1 + math.cos(w0)) / (2.0 * a0)
    return params

def bq_lopass(freq, q):
    params = {}
    w0 = 2 * math.pi * freq / MFPApp().samplerate
    alpha = math.sin(w0) / (2*q)
    a0 = 1 + alpha
    params['a1'] = (-2.0*math.cos(w0)) / a0
    params['a2'] = (1 - alpha) / a0
    params['b0'] = (1 - math.cos(w0)) / (2.0 * a0)
    params['b1'] = (1 - math.cos(w0)) / a0
    params['b2'] = (1 - math.cos(w0)) / (2.0 * a0)
    return params

def bq_bandpass(freq, q):
    params = {}
    w0 = 2 * math.pi * freq / MFPApp().samplerate
    alpha = math.sin(w0) / (2*q)
    a0 = 1 + alpha
    params['a1'] = (-2.0*math.cos(w0)) / a0
    params['a2'] = (1 - alpha) / a0
    params['b0'] = alpha / a0
    params['b1'] = 0
    params['b2'] = -1.0 * alpha / a0
    return params

class BiquadWrapper(Processor):
    doc_tooltip_obj = "%s filter (biquad implementation)"
    doc_tooltip_inlet = ["Signal in",
                         "Frequency of interest (default: initarg 0)",
                         "Q (filter steepness) (default: initarg 1)"]
    doc_tooltip_outlet = ["Signal out"]

    def __init__(self, bq_func, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 3, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        if len(initargs) > 0:
            self.freq = initargs[0]
        else:
            self.freq = 0

        if len(initargs) > 1:
            self.q = initargs[1]
        else:
            self.q = 0.707

        self.biquad_thunk = bq_func
        self.biquad_params = self.biquad_thunk(self.freq, self.q)

        self.hot_inlets = [0, 1, 2]
        self.dsp_inlets = [0]
        self.dsp_outlets = [0]

    async def setup(self):
        await self.dsp_init("biquad~", **self.biquad_params)

    async def trigger(self):
        recalc = False
        if self.inlets[1] is not Uninit:
            self.freq = self.inlets[1]
            recalc = True
        if self.inlets[2] is not Uninit:
            self.q = self.inlets[2]
            recalc = True
        if recalc:
            self.biquad_params = self.biquad_thunk(self.freq, self.q)
            for n, v in self.biquad_params.items():
                await self.dsp_setparam(n, float(v))


def mk_biquad(thunk, filter_name):
    def factory(init_type, init_args, patch, scope, name):
        bq = BiquadWrapper(thunk, init_type, init_args, patch, scope, name)
        bq.doc_tooltip_obj = BiquadWrapper.doc_tooltip_obj % filter_name
        return bq

    return factory


def register():
    MFPApp().register("biquad~", Biquad)
    MFPApp().register("hip~", mk_biquad(bq_hipass, "Highpass"))
    MFPApp().register("lop~", mk_biquad(bq_lopass, "Lowpass"))
    MFPApp().register("bp~", mk_biquad(bq_bandpass, "Bandpass"))
