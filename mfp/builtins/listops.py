#! /usr/bin/env python
'''
p_listops.py: Wrappers for common list operations

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''
from mfp import log, Bang
from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit

class Pack (Processor):
    doc_tooltip_obj = "Collect inputs into a list"
    doc_tooltip_outlet = [ "List output" ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)
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

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        extra=defs or {}
        initargs, kwargs = patch.parse_args(init_args, **extra)

        if len(initargs):
            num_outlets = initargs[0] + 1
        else:
            num_outlets = 1
        Processor.__init__(self, 1, num_outlets, init_type, init_args, patch, scope, name, defs)
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

class Hodor (Processor):
    doc_tooltip_obj = "Hold the hot input to reverse output order"
    doc_tooltip_inlet = [ "Inlet 0", "Inlet 1" ]
    doc_tooltip_outlet = [ "Outlet 0", "Outlet 1" ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 2, 2, init_type, init_args, patch, scope, name, defs)
        self.hot_inlets = [1]

    async def trigger(self):
        self.outlets[0] = self.inlets[0]
        self.outlets[1] = self.inlets[1]


class Append (Processor):
    doc_tooltip_obj = "Append an item to a list or string"
    doc_tooltip_inlet = [ "List to append to", "Item to append"]
    doc_tooltip_outlet = [ "List output" ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)
        if len(initargs):
            self.inlets[1] = initargs[0]
        else:
            self.inlets[1] = []

    async def trigger(self):
        if isinstance(self.inlets[0], str):
            newval = self.inlets[0] + str(self.inlets[1])
        else:
            newval = [v for v in list(self.inlets[0])] + [self.inlets[1]]
        self.outlets[0] = newval


class Zip (Processor):
    doc_tooltip_obj = "Merge input lists by item"
    doc_tooltip_outlet = [ "List output" ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        extra=defs or {}
        initargs, kwargs = patch.parse_args(init_args, **extra)

        if len(initargs):
            num_inlets = initargs[0]
        else:
            num_inlets = 1
        self.doc_tooltip_inlet = []
        for i in range(num_inlets):
            self.doc_tooltip_inlet.append("List %d input" % i)

        Processor.__init__(self, num_inlets, 1, init_type, init_args, patch, scope, name, defs)

    async def trigger(self):
        if len(self.inlets) == 1:
            self.outlets[0] = list(zip(*self.inlets[0]))
        else:
            self.outlets[0] = list(zip(*self.inlets))

class Sort (Processor):
    doc_tooltip_obj = "Sort a list"
    doc_tooltip_inlet = [ "List", "Key function (default: element)" ]
    doc_tooltip_outlet = [ "List output" ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = patch.parse_args(init_args, **extra)

        self.func = lambda x: x
        if len(initargs):
            self.func = initargs[0]

    async def trigger(self):
        if self.inlets[1] != Uninit:
            self.func = self.inlets[1]
        self.outlets[0] = list(sorted(self.inlets[0], key=self.func))


class Map (Processor):
    doc_tooltip_obj = "Apply a function to each list element"
    doc_tooltip_inlet = [ "List", "Function to apply (default: initarg 1)"]
    doc_tooltip_outlet = [ "List output" ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = patch.parse_args(init_args, **extra)

        self.func = lambda x: x
        if len(initargs):
            self.func = initargs[0]

    async def trigger(self):
        if self.inlets[1] != Uninit:
            self.func = self.inlets[1]
        self.outlets[0] = list(map(self.func, self.inlets[0]))


class Filter (Processor):
    doc_tooltip_obj = "Pass through elements if the function returns True"
    doc_tooltip_inlet = [ "List", "Function or sequence to apply (default: initarg 1)"]
    doc_tooltip_outlet = [ "List output" ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = patch.parse_args(init_args, **extra)

        self.func = lambda x: x
        if len(initargs):
            self.func = initargs[0]

    async def trigger(self):
        if self.inlets[1] != Uninit:
            self.func = self.inlets[1]

        if callable(self.func):
            self.outlets[0] = list(filter(self.func, self.inlets[0]))
        elif isinstance(self.func, (list, tuple)):
            self.outlets[0] = [
                f for pos, f in enumerate(self.inlets[0]) if self.func[pos]
            ]


class Slice (Processor):
    doc_tooltip_obj = "Extract a slice of an iterable"
    doc_tooltip_inlet = ["List", "Start element (default: initarg 0)",
                         "End element (default: initarg 1)",
                         "Stride (default: initarg 2)"]
    doc_tooltip_outlet = [ "List output" ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 4, 1, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = patch.parse_args(init_args, **extra)

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


class Range (Processor):
    doc_tooltip_obj = "Produce a list with a range of values"
    doc_tooltip_inlet = [
        "Tuple/list of (start, end, stride)"
    ]
    doc_tooltip_outlet = [ "List output" ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = patch.parse_args(init_args, **extra)

        self.default_start = 0
        self.default_stride = 1
        if len(initargs):
            self.default_start = initargs[0]
        if len(initargs) > 1:
            self.default_stride = initargs[1]

    async def trigger(self):
        if isinstance(self.inlets[0], (int, float)):
            params = (self.default_start, self.inlets[0], self.default_stride)
        else:
            params = list(self.inlets[0])
            if len(params) == 1:
                params = [self.default_start, params[0], self.default_stride]
            elif len(params) == 2:
                params = [params[0], params[1], self.default_stride]

        self.outlets[0] = list(range(*params))


def register():
    MFPApp().register("pack", Pack)
    MFPApp().register("unpack", Unpack)
    MFPApp().register("hodor", Hodor)
    MFPApp().register("zip", Zip)
    MFPApp().register("append", Append)
    MFPApp().register("map", Map)
    MFPApp().register("filter", Filter)
    MFPApp().register("sort", Sort)
    MFPApp().register("slice", Slice)
    MFPApp().register("range", Range)
