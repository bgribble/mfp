#! /usr/bin/env python2.6
'''
p_listops.py: Wrappers for common list operations

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp

class Pack (Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            num_inlets = initargs[0]
        else:
            num_inlets = 1
        self.resize(num_inlets, 1)

    def trigger(self):
        self.outlets[0] = self.inlets


class Unpack (Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        if len(initargs):
            num_outlets = initargs[0] + 1
        else:
            num_outlets = 1
        self.resize(1, num_outlets)
        self.outlet_order.reverse()

    def trigger(self):
        nout = len(self.outlets) - 1 
        for n in range(nout):
            self.outlets[n] = self.inlets[0][n]

        self.outlets[-1] = self.inlets[nout:]


def list_car(ll):
    return ll[0]


def list_cdr(ll):
    return ll[1:]


def register():
    MFPApp().register("pack", Pack)
    MFPApp().register("unpack", Unpack)

