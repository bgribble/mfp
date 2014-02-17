#! /usr/bin/env python2.6
'''
trigger.py: Repeat input on multiple outputs

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit


class Trigger (Processor):
    doc_tooltip_obj = "Pass through input to N outputs, in right-to-left order" 
    doc_tooltip_inlet = [ "Passthru input" ]

    '''
    [trigger {n}]

    [trigger] clones its input on multiple outputs, number
    determined by the creation arg.  Used as a sequencing aid,
    since outputs will be activated in reverse order of index
    '''
    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args)
        if len(initargs) > 0:
            numout = initargs[0]
        else:
            numout = 1
        self.resize(1, numout)
        self.outlet_order.reverse()

        self.doc_tooltip_outlet = [] 
        for i in range(numout):
            self.doc_tooltip_outlet.append("Output %d" % (numout-i,))

    def trigger(self):
        for i in range(len(self.outlets)):
            self.outlets[i] = self.inlets[0]
        self.inlets[0] = Uninit


def register():
    MFPApp().register("trigger", Trigger)
