#! /usr/bin/env python
'''
dbmath.py: dB/gain conversions

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp
from mfp.bang import Uninit 
import math

class Ampl2DB(Processor):

    doc_tooltip_obj = "Convert amplitude to dB values"
    doc_tooltip_inlet = ["Value to convert to dB", 
                         "0dB reference level (default: initarg 0, or 1.0)"]
    doc_tooltip_outlet = ["dB value"] 

    def __init__(self, init_type, init_args, patch, scope, name):
        self.dbref = 1.0 
        self.lowlow = -1000

        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            self.dbref = initargs[0]

    async def trigger(self):
        if self.inlets[1] is not Uninit:
            self.dbref = self.inlets[1]
        try: 
            self.outlets[0] = 20*math.log10(self.inlets[0] / self.dbref)
        except ValueError:
            self.outlets[0] = self.lowlow


class DB2Ampl(Processor):

    doc_tooltip_obj = "Convert dB to amplitude/gain"
    doc_tooltip_inlet = ["dB value to convert", 
                         "0dB reference level (default: initarg 0, or 1.0)"]
    doc_tooltip_outlet = ["Amplitude value"]

    def __init__(self, init_type, init_args, patch, scope, name):
        self.dbref = 1.0 
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            self.dbref = initargs[0]

    async def trigger(self):
        if self.inlets[1] is not Uninit:
            self.dbref = self.inlets[1]

        self.outlets[0] = math.pow(10, (self.inlets[0] / 20.0)) * self.dbref

def register():
    MFPApp().register("db2a", DB2Ampl)
    MFPApp().register("a2db", Ampl2DB)





