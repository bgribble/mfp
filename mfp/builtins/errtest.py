
#! /usr/bin/env python
'''
errtest.py: Error test helper (not of use unless you want to crash MFP)

Copyright (c) 2014 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp


class ErrtestSig (Processor):
    doc_tooltip_obj = "Error test helper"
    dsp_type = "errtest~"

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)

        if len(initargs):
            size = initargs[0] 
        else: 
            size = 0

        self.dsp_inlets = [0]
        self.dsp_outlets = [0]

    async def setup(self, **kwargs):
        await self.dsp_init(self.dsp_type)

def register():
    MFPApp().register("errtest~", ErrtestSig)
