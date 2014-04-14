#! /usr/bin/env python2.6
'''
arith.py:  Builtin arithmetic DSP ops

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp


class ArithProcessor(Processor):
    doc_tooltip_obj = "Signal arithmetic"
    doc_tooltip_inlet = [ "Input signal", "Input signal (default: initarg 0)"]
    doc_tooltip_outlet = [ "Output signal" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        self.arith_op = init_type

        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
    
        const = 0.0
        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            const = initargs[0] 

        self.dsp_inlets = [0, 1]
        self.dsp_outlets = [0]
        self.dsp_init(self.arith_op, _sig_1=const)

    def trigger(self): 
        pass 

class ArithAdd(ArithProcessor):
    doc_tooltip_obj = "Add signals" 
    pass


class ArithSub(ArithProcessor):
    doc_tooltip_obj = "Subtract signals" 
    pass


class ArithMul(ArithProcessor):
    doc_tooltip_obj = "Multiply signals" 
    pass


class ArithDiv(ArithProcessor):
    doc_tooltip_obj = "Divide signals" 
    pass


class ArithLt(ArithProcessor):
    doc_tooltip_obj = "Compare signals" 
    doc_tooltip_outlet = [ "Output signal (boolean)" ]
    pass


class ArithGt (ArithProcessor):
    doc_tooltip_obj = "Compare signals" 
    doc_tooltip_outlet = [ "Output signal (boolean)" ]
    pass


def register():
    MFPApp().register("+~", ArithAdd)
    MFPApp().register("-~", ArithSub)
    MFPApp().register("*~", ArithMul)
    MFPApp().register("/~", ArithDiv)
    MFPApp().register(">~", ArithGt)
    MFPApp().register("<~", ArithLt)
