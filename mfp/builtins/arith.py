#! /usr/bin/env python2.6
'''
arith.py:  Builtin arithmetic DSP ops

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from mfp.main import MFPApp


class ArithProcessor(Processor):
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
    pass


class ArithSub(ArithProcessor):
    pass


class ArithMul(ArithProcessor):
    pass


class ArithDiv(ArithProcessor):
    pass


class ArithLt(ArithProcessor):
    pass


class ArithGt (ArithProcessor):
    pass


def register():
    MFPApp().register("+~", ArithAdd)
    MFPApp().register("-~", ArithSub)
    MFPApp().register("*~", ArithMul)
    MFPApp().register("/~", ArithDiv)
    MFPApp().register(">~", ArithGt)
    MFPApp().register("<~", ArithLt)
