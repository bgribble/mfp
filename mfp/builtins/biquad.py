#! /usr/bin/env python2.6
'''
biquad.py: Biquad filter implementation

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from mfp.main import MFPApp
from mfp import log
import math 
from ..bang import Uninit 

class Biquad(Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        self.dsp_inlets = [0]
        self.dsp_outlets = [0]
        self.dsp_init("biquad~")

    def trigger(self):
        if isinstance(self.inlets[0], dict):
            for param, val in self.inlets[0].items():
                try:
                    self.dsp_setparam(param, float(val))
                except Exception, e:
                    log.debug("biquad~: Error setting param", param, "to", type(val), str(val))
                    log.debug("biquad~: Exception:", str(e))


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
        self.dsp_init("biquad~", **self.biquad_params)

    def trigger(self):
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
                self.dsp_setparam(n, float(v))

def mk_biquad(thunk):
    def factory(init_type, init_args, patch, scope, name):
        return BiquadWrapper(thunk, init_type, init_args, patch, scope, name)

    return factory 

def register():
    MFPApp().register("biquad~", Biquad)
    MFPApp().register("hip~", mk_biquad(bq_hipass))
    MFPApp().register("lop~", mk_biquad(bq_lopass))
    MFPApp().register("bp~", mk_biquad(bq_bandpass))

