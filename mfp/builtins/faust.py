#! /usr/bin/env python
'''
faust.py:  Builtin faust DSP object

Inlets and outlets are dynamically created after the Faust
compiler runs.

*



Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp
from .. import Bang, Uninit
from mfp import log


class Faust(Processor):
    doc_tooltip_obj = "Compile and execute Faust code"
    doc_tooltip_inlet = []
    doc_tooltip_outlet = []

    RESP_PARAM = 0
    RESP_DSP_INLETS = 1
    RESP_DSP_OUTLETS = 2

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 1, 0, init_type, init_args, patch, scope, name, defs)
        extra = defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)

        self.faust_filename = None
        self.faust_code = None

        if "code" in kwargs:
            self.faust_code = kwargs["code"]
        elif "filename" in kwargs:
            self.faust_filename = kwargs["filename"]
            self.faust_code = open(self.faust_filename).read()
        else:
            self.faust_code = extra.get("faust_code", "")

        # info returned after compiling the fause code
        # faust_params are the names of sliders and other UI elements
        # faust_dsp_XXlets are the number of DSP inlets/outlets in the
        # Faust process
        self.faust_params = []
        self.faust_dsp_inlets = 0
        self.faust_dsp_outlets = 0

        # dsp inlets and outlets are dynamically created to match the
        # Faust process
        self.dsp_inlets = []
        self.dsp_outlets = []

        self.set_channel_tooltips()

    async def setup(self):
        await self.dsp_init("faust~", faust_code=self.faust_code)

    def set_channel_tooltips(self):
        self.doc_tooltip_inlet = [
            "Signal input 0/control messages" if self.faust_dsp_inlets else "Control messages",
            *[
                f"Signal input {n}"
                for n in range(1, self.faust_dsp_inlets)
            ],
            *[
                f"{p} input"
                for p in self.faust_params
            ]
        ]
        self.doc_tooltip_outlet = [
            *[
                f"Signal output {n}"
                for n in range(self.faust_dsp_outlets)
            ]
        ]

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
        need_conf = False
        if (
            len(self.dsp_inlets) != self.faust_dsp_inlets
            or len(self.dsp_outlets) != self.faust_dsp_outlets
        ):
            need_conf = True

        self.dsp_inlets = list(range(self.faust_dsp_inlets))
        self.dsp_outlets = list(range(self.faust_dsp_outlets))
        self.hot_inlets = list(range(inlets))

        if need_conf:
            self.conf(dsp_inlets=self.dsp_inlets, dsp_outlets=self.dsp_outlets)
        self.set_channel_tooltips()

    async def trigger(self):
        for inlet_num, value in enumerate(self.inlets):
            if value != Uninit:
                if inlet_num >= self.faust_dsp_inlets:
                    param = self.faust_params[inlet_num - self.faust_dsp_inlets]
                    await self.dsp_setparam(param, value)

def register():
    MFPApp().register("faust~", Faust)
