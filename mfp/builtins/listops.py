#! /usr/bin/env python
'''
p_listops.py: Wrappers for common list operations

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''
from mfp import log
from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit

class Pack (Processor):
    doc_tooltip_obj = "Collect inputs into a list" 
    doc_tooltip_outlet = [ "List output" ]

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
            self.doc_tooltip_inlet.append("List item %d input" % i) 


    async def trigger(self):
        self.outlets[0] = [l for l in self.inlets]

class Unpack (Processor):
    doc_tooltip_obj = "Break list into items" 
    doc_tooltip_inlet = [ "List input"] 

    def __init__(self, init_type, init_args, patch, scope, name):
        initargs, kwargs = patch.parse_args(init_args)

        if len(initargs):
            num_outlets = initargs[0] + 1
        else:
            num_outlets = 1
        Processor.__init__(self, 1, num_outlets, init_type, init_args, patch, scope, name)
        self.outlet_order.reverse()
        self.doc_tooltip_outlet = [] 
        for i in range(num_outlets-1):
            self.doc_tooltip_outlet.append("List item %d output" % i)
        self.doc_tooltip_outlet.append("Rest of list output")

    async def trigger(self):
        nout = len(self.outlets) - 1 
        for n in range(nout):
            try:
                self.outlets[n] = self.inlets[0][n]
            except IndexError:
                pass

        self.outlets[-1] = self.inlets[0][nout:]


class Append (Processor):
    doc_tooltip_obj = "Append an item to a list"
    doc_tooltip_inlet = ["Item to append", "List to append to"]
    doc_tooltip_outlet = [ "List output" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            self.inlets[1] = initargs[0]
        else:
            self.inlets[1] = []

    async def trigger(self):
        import copy
        new_list = copy.copy(self.inlets[1])
        new_list.append(self.inlets[0])
        self.outlets[0] = new_list


class Zip (Processor):
    doc_tooltip_obj = "Merge input lists by item"
    doc_tooltip_outlet = [ "List output" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        initargs, kwargs = patch.parse_args(init_args)

        if len(initargs):
            num_inlets = initargs[0]
        else:
            num_inlets = 1
        self.doc_tooltip_inlet = [] 
        for i in range(num_inlets):
            self.doc_tooltip_inlet.append("List %d input" % i)

        Processor.__init__(self, num_inlets, 1, init_type, init_args, patch, scope, name)

    async def trigger(self):
        if len(self.inlets) == 1:
            self.outlets[0] = list(zip(*self.inlets[0]))
        else: 
            self.outlets[0] = list(zip(*self.inlets))

class Map (Processor):
    doc_tooltip_obj = "Apply a function to each list element"
    doc_tooltip_inlet = [ "List", "Function to apply (default: initarg 1)"]
    doc_tooltip_outlet = [ "List output" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = patch.parse_args(init_args)
        
        self.func = lambda x: x 
        if len(initargs):
            self.inlets[1] =  initargs[0]


    async def trigger(self):
        self.outlets[0] = list(map(self.inlets[1], self.inlets[0]))


class Slice (Processor):
    doc_tooltip_obj = "Extract a slice of an iterable"
    doc_tooltip_inlet = ["List", "Start element (default: initarg 0)", 
                         "End element (default: initarg 1)", 
                         "Stride (default: initarg 2)"]
    doc_tooltip_outlet = [ "List output" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 4, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = patch.parse_args(init_args)
        
        self.func = lambda x: x 
        if len(initargs) > 2:
            self.inlets[3] = initargs[2]
        if len(initargs) > 1:
            self.inlets[2] = initargs[1]
        if len(initargs) > 0:
            self.inlets[1] = initargs[0]

    async def trigger(self):
        start = self.inlets[1] if self.inlets[1] is not Uninit else None
        stop = self.inlets[2] if self.inlets[2] is not Uninit else None
        stride  = self.inlets[3] if self.inlets[3] is not Uninit else 1
        slicer = slice(start, stop, stride)
        self.outlets[0] = self.inlets[0][slicer]




def register():
    MFPApp().register("pack", Pack)
    MFPApp().register("unpack", Unpack)
    MFPApp().register("zip", Zip)
    MFPApp().register("append", Append)
    MFPApp().register("map", Map)
    MFPApp().register("slice", Slice)



