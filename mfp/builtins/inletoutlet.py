'''
p_inletoutlet.py: inlet and outlet processors for patches

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor, AsyncOutput
from ..mfp_app import MFPApp
from .. import Uninit

from mfp import log

class Inlet(Processor):
    doc_tooltip_obj = "Message input to patch"
    doc_tooltip_cold = "Message input to patch"
    doc_tooltip_hot = "Message input to patch (hot)"

    do_onload = False

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        extra=defs or {}
        if patch:
            initargs, kwargs = patch.parse_args(init_args, **extra)
        else:
            initargs = []

        if len(initargs):
            self.inletnum = initargs[0]
        elif patch is not None:
            self.inletnum = len(patch.inlet_objects)
            init_args = str(self.inletnum)
        else:
            self.inletnum = 0
            init_args = "0"

        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name, defs)
        if self.inletnum in patch.hot_inlets:
            self.doc_tooltip_obj = self.doc_tooltip_hot
        else:
            self.doc_tooltip_obj = self.doc_tooltip_cold

    async def clone(self, patch, scope, name):
        # for inlet and outlet, always clear initargs so an xlet number is
        # selected automatically
        prms = self.save()
        if self.inletnum in patch.hot_inlets:
            hot = True
        else:
            hot = False

        newobj = await MFPApp().create(prms.get("type"), None, patch, scope, name)
        newobj.load(prms)
        if hot:
            newobj.hot()
        return newobj

    def hot(self):
        if self.inletnum not in self.patch.hot_inlets:
            self.patch.hot_inlets.append(self.inletnum)
            self.doc_tooltip_obj = self.doc_tooltip_hot

    def cold(self):
        if self.inletnum in self.patch.hot_inlets:
            self.patch.hot_inlets.remove(self.inletnum)
            self.doc_tooltip_obj = self.doc_tooltip_cold

    async def trigger(self):
        self.outlets[0] = self.inlets[0]
        self.inlets[0] = Uninit


class SignalInlet(Inlet):
    doc_tooltip_obj = "Signal input to patch"

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Inlet.__init__(self, init_type, init_args, patch, scope, name, defs)
        self.dsp_outlets = [0]
        self.dsp_inlets = [0]

    async def setup(self):
        await self.dsp_init("inlet~", io_channel=self.inletnum)


class Outlet(Processor):
    doc_tooltip_obj = "Message output from patch"
    do_onload = False
    clear_outlets = False

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        extra=defs or {}
        if patch:
            initargs, kwargs = patch.parse_args(init_args, **extra)
        else:
            initargs = []

        if len(initargs):
            self.outletnum = initargs[0]
        elif patch is not None:
            self.outletnum = len(patch.outlet_objects)
            init_args = str(self.outletnum)
        else:
            self.outletnum = 0
            init_args = "0"

        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name, defs)

    async def clone(self, patch, scope, name):
        # for inlet and outlet, always clear initargs so an xlet number is
        # selected automatically

        prms = self.save()
        newobj = await MFPApp().create(prms.get("type"), None, patch, scope, name)
        newobj.load(prms)
        return newobj

    async def trigger(self):
        in_value = self.inlets[0]
        self.inlets[0] = Uninit

        self.add_output(0, in_value)


class SignalOutlet(Outlet):
    doc_tooltip_obj = "Signal output from patch"

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Outlet.__init__(self, init_type, init_args, patch, scope, name, defs)
        self.dsp_outlets = [0]
        self.dsp_inlets = [0]

    async def setup(self):
        await self.dsp_init("outlet~", io_channel=self.outletnum)


def register():
    MFPApp().register("inlet", Inlet)
    MFPApp().register("outlet", Outlet)
    MFPApp().register("inlet~", SignalInlet)
    MFPApp().register("outlet~", SignalOutlet)
