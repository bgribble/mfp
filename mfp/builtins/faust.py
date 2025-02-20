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

    RESP_PARAM = 0
    RESP_DSP_INLETS = 1
    RESP_DSP_OUTLETS = 2

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 1, 0, init_type, init_args, patch, scope, name)
        extra = defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)

        self.faust_code = extra.get("faust_code", "")
        self.faust_params = []
        self.faust_dsp_inlets = 0
        self.faust_dsp_outlets = 0

        self.dsp_inlets = []
        self.dsp_outlets = []

    async def setup(self):
        await self.dsp_init( "faust~", faust_code=self.faust_code)

    def dsp_response(self, resp_id, resp_value):
        if resp_id == self.RESP_DSP_INLETS:
            self.faust_dsp_inlets = resp_value
        elif resp_id == self.RESP_DSP_OUTLETS:
            self.faust_dsp_outlets = resp_value
        elif resp_id == self.RESP_PARAM:
            self.faust_params.append(resp_value)

        inlets = max(1, self.faust_dsp_inlets + len(self.faust_params))
        self.resize(
            inlets,
            self.faust_dsp_outlets
        )
        self.dsp_inlets = list(range(self.faust_dsp_inlets))
        self.dsp_outlets = list(range(self.faust_dsp_outlets))
        self.hot_inlets = list(range(inlets))

    async def trigger(self):
        for inlet_num, value in enumerate(self.inlets):
            if value != Uninit:
                param = self.faust_params[inlet_num]
                await self.dsp_setparam(param, value)

def register():
    MFPApp().register("faust~", Faust)
