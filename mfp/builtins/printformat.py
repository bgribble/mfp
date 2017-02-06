#! /usr/bin/env python
'''
printformat.py: Debugging print processor

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit
from mfp import log


class Print (Processor):
    doc_tooltip_obj = "Print input to log window, formatting with Python %% operator" 
    doc_tooltip_inlet = [ "Object to print", "Format string (default: initarg 0)" ]
    doc_tooltip_outlet = [ "Object formatted as a string" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            self.format_string = initargs[0]
        else:
            self.format_string = None

    def trigger(self):
        if self.inlets[1] is not Uninit:
            self.format_string = self.inlets[1]

        if self.inlets[0] is not Uninit:
            out = None 
            if self.format_string is None:
                out = str(self.inlets[0])
            elif '%' in self.format_string:
                try:
                    out = self.format_string % self.inlets[0]
                except TypeError as e:
                    pass
            if out is None:
                if not self.format_string:
                    leader = ''
                else:
                    leader = self.format_string + ' '

                out = leader + str(self.inlets[0])

            self.outlets[0] = out
            if self.init_type == "print":
                log.logprint(out)

class Format (Print):
    doc_tooltip_obj = "Format input strings with Python %% operator"


def register():
    MFPApp().register("print", Print)
    MFPApp().register("format", Format)
