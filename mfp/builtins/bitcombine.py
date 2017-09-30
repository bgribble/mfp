#! /usr/bin/env python
'''
bitmux.py: combine and split bits 

Copyright (c) 2017 Bill Gribble <grib@billgribble.com>
'''

from mfp import log
from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit

class BitCombine (Processor):
    doc_tooltip_obj = "Combine bits into a numeric value" 
    doc_tooltip_outlet = [ "Combined" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            num_inlets = initargs[0]
        else:
            num_inlets = 1
        self.resize(num_inlets, 1)

        self.doc_tooltip_inlet = []
        for i in range(num_inlets): 
            self.doc_tooltip_inlet.append("Bit %d (%s) input" % (i, 2**i)) 

    def trigger(self):
        bits = [i and 1 or 0 for i in self.inlets]
        self.outlets[0] = sum(
            val * 2**ind
            for ind, val in enumerate(bits)
        )

class BitSplit(Processor):
    doc_tooltip_obj = "Combine bits into a numeric value" 
    doc_tooltip_outlet = [ "Combined" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            num_outlets = initargs[0]
        else:
            num_outlets = 1
        self.resize(1, num_outlets)

        self.doc_tooltip_outlet = []
        for i in range(num_outlets): 
            self.doc_tooltip_outlet.append("Bit %d (%s) output" % (i, 2**i)) 

    def trigger(self):
        remainder = int(self.inlets[0])
        for bitnum in range(len(self.outlets)):
            self.outlets[bitnum] = remainder & 1
            remainder = remainder >> 1

def register():
    MFPApp().register('bitcombine', BitCombine)
    MFPApp().register('bitsplit', BitSplit)

