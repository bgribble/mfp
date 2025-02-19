#! /usr/bin/env python
'''
faust.py:  Builtin faust DSP object

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp
from .. import Bang, Uninit
from mfp import log


class Faust(Processor):
    doc_tooltip_obj = "Compile and execute Faust code"
    doc_tooltip_inlet = []
    doc_tooltip_outlet = ["Signal output"]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
        extra = defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)

        self.faust_code = extra.get("faust_code", "")
        self.dsp_inlets = [0]
        self.dsp_outlets = [0]

    async def setup(self):
        await self.dsp_init(
            "faust~",
            faust_code=self.faust_code
        )
        log.debug(f"[faust~] init done")

    async def trigger(self):
        return

def register():
    MFPApp().register("faust~", Faust)
