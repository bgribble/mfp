#! /usr/bin/env python
'''
loop.py:  Builtin iteration constructs

Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp
from mfp.bang import Bang, Uninit
from mfp import log

def iterable(o):
    try:
        getattr(o, '__getitem__')
        return True
    except AttributeError as e:
        return False


class For(Processor):
    doc_tooltip_obj = "Emit an input list one item at a time"
    doc_tooltip_inlet = ["List or control input (True/Bang to start, False to stop)",
                         "List to iterate (default: initarg 0)"]
    doc_tooltip_outlet = ["List item output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        self.iterating = False
        self.startval = False
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            self.inlets[1] = initargs[0]
            self.startval = initargs[0]

    async def trigger(self):
        if self.inlets[0] is False:
            self.iterating = False
            return
        elif self.iterating:
            return
        elif iterable(self.inlets[0]):
            self.inlets[1] = self.inlets[0]
            self.startval = self.inlets[0]
            self.inlets[0] = Uninit
            self.iterating = True
        elif self.inlets[0] in (Bang, True):
            self.iterating = True
            self.startval = self.inlets[1]

        while self.iterating and iterable(self.inlets[1]) and len(self.inlets[1]) > 0:
            val = self.inlets[1][0]
            self.inlets[1] = self.inlets[1][1:]
            for target, inlet in self.connections_out[0]:
                await target.send(val, inlet)
                if self.inlets[0] is False:
                    self.iterating = False
                    break

        self.iterating = False
        self.inlets[1] = self.startval


def register():
    MFPApp().register("for", For)
