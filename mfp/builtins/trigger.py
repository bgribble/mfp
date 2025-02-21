#! /usr/bin/env python
'''
trigger.py: Repeat input on multiple outputs

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit, Bang


class Trigger (Processor):
    doc_tooltip_obj = "Pass through input to N outputs, in right-to-left order"
    doc_tooltip_inlet = ["Passthru input"]
    doc_help_patch = "trigger.help.mfp"

    '''
    [trigger {n}] or
    [trigger {type}, {type} ...]

    [trigger] clones its input on multiple outputs, number
    determined by the creation args.  Used as a sequencing aid,
    since outputs will be activated in reverse order of index

    Optionally type-converts before outputting. Any callable of 1
    arg can be used as a converter; in this context shortcut variables
    are defined for common conversions:

    a [any] - do no conversion
    b [bang] - output a bang for any input
    f [float] - output a float with float(v)
    i [int] - output an integer with int(v)
    s [str] - output a string
    '''

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name, defs)

        extra_bindings = dict(
            f=float, i=int, n=float, s=str,
            a=lambda v: v, b=lambda v: Bang
        )

        initargs, kwargs = self.parse_args(init_args, **extra_bindings)
        if len(initargs) > 0 and isinstance(initargs[0], (float, int)):
            numout = int(initargs[0])
            self.converters = [lambda v: v] * numout
        else:
            numout = len(initargs)
            self.converters = [*initargs]

        self.resize(1, numout)

        self.doc_tooltip_outlet = []
        for i in range(numout):
            self.doc_tooltip_outlet.append("Output %d" % (numout-i,))

    async def trigger(self):
        for i in range(len(self.outlets)):
            self.outlets[i] = self.converters[i](self.inlets[0])
        self.inlets[0] = Uninit

def register():
    MFPApp().register("trigger", Trigger)
    MFPApp().register("t", Trigger)
