#! /usr/bin/env python
'''
dispatch.py: Method dispatch builtins for user patches 

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit
from ..method import MethodCall

class Dispatch (Processor):
    doc_tooltip_obj = "Receive method call objects for the patch"
    doc_tooltip_outlet = [ "Output (name, methodcall) tuples" ]
    '''
    [dispatch]

    [dispatch] is used by the Patch object to inject MethodCall 
    objects for handling within the patch. 
    '''

    def __init__(self, init_type, init_args, patch, scope, name): 
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

    def method(self, value, inlet):
        self.trigger()

    async def trigger(self):
        if isinstance(self.inlets[0], MethodCall):
            self.outlets[0] = (self.inlets[0].method, self.inlets[0])
            self.inlets[0] = Uninit 

class BaseClass (Processor):
    doc_tooltip_obj = "Pass method call objects to the Patch base class"
    doc_tooltip_inlet = "MethodCall inlet"

    '''
    [baseclass] 

    Use as the default handler after a [dispatch] - [route] block.  Will attempt
    to call the method on Patch/Processor.
    '''
    def __init__(self, init_type, init_args, patch, scope, name): 
        Processor.__init__(self, 1, 0, init_type, init_args, patch, scope, name)

    async def trigger(self):
        if isinstance(self.inlets[0], (list, tuple)):
            name, obj = self.inlets[0] 
            if isinstance(obj, MethodCall):
                self.patch.baseclass_method(obj)


def register():
    MFPApp().register("dispatch", Dispatch)
    MFPApp().register("baseclass", BaseClass)
