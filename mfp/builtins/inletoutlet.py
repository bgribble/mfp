#! /usr/bin/env python2.6
'''
p_inletoutlet.py: inlet and outlet processors for patches

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp
from .. import Uninit


class Inlet(Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        if patch:
            initargs, kwargs = patch.parse_args(init_args)
        else:
            initargs = []
            kwargs = {}

        if len(initargs):
            self.inletnum = initargs[0]
        elif patch is not None:
            self.inletnum = len(patch.inlet_objects)
            init_args = str(self.inletnum)
            print "setting inletnum to", self.inletnum
        else:
            self.inletnum = 0
            init_args = "0"

        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

    def trigger(self):
        self.outlets[0] = self.inlets[0]
        self.inlets[0] = Uninit


class Outlet(Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        if patch:
            initargs, kwargs = patch.parse_args(init_args)
        else:
            initargs = []
            kwargs = {}

        if len(initargs):
            self.outletnum = initargs[0]
        elif patch is not None:
            self.outletnum = len(patch.outlet_objects)
            self.init_args = str(self.outletnum)
        else:
            self.outletnum = 0
            init_args = "0"

        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

    def trigger(self):
        if self.patch:
            self.patch.outlets[self.outletnum] = self.inlets[0]

        self.outlets[0] = self.inlets[0]
        self.inlets[0] = Uninit


def register():
    MFPApp().register("inlet", Inlet)
    MFPApp().register("outlet", Outlet)
