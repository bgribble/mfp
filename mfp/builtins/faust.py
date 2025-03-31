#! /usr/bin/env python
'''
faust.py:  Builtin faust DSP object

Inlets and outlets are dynamically created after the Faust
compiler runs.

Copyright (c) Bill Gribble <grib@billgribble.com>
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

        # info returned after compiling the faust code
        # faust_params are the names of sliders and other UI elements
        # faust_dsp_XXlets are the number of DSP inlets/outlets in the
        # Faust process
        self.faust_params = []
        self.faust_dsp_inlets = 0
        self.faust_dsp_outlets = 0
        self.faust_initialized = []

        # dsp inlets and outlets are dynamically created to match the
        # Faust process
        self.dsp_inlets = []
        self.dsp_outlets = []

        self.set_channel_tooltips()

    def save(self):
        """
        faust_params will get set when a new Faust program is
        compiled, but we want to save it here so that when
        we reload the patch we configure the processor correctly
        even though we haven't compiled the code just yet
        """
        base_dict = super().save()
        base_dict['faust_params'] = self.faust_params
        base_dict['faust_dsp_inlets'] = self.faust_dsp_inlets
        base_dict['faust_dsp_outlets'] = self.faust_dsp_outlets
        return base_dict

    def load(self, prms):
        super().load(prms)
        self.faust_params = prms.get("faust_params", [])
        self.faust_dsp_inlets = prms.get("faust_dsp_inlets", 0)
        self.faust_dsp_outlets = prms.get("faust_dsp_outlets", 0)

        num_inlets = max(1, self.faust_dsp_inlets + len(self.faust_params))
        num_outlets = self.faust_dsp_outlets
        self.dsp_inlets = list(range(self.faust_dsp_inlets))
        self.dsp_outlets = list(range(self.faust_dsp_outlets))
        self.inlets = [Uninit] * num_inlets
        self.outlets = [Uninit] * num_outlets
        self.connections_out = [[] for r in range(num_outlets)]
        self.connections_in = [[] for r in range(num_inlets)]
        self.outlet_order = list(reversed(range(num_outlets)))

        self.gui_params['num_inlets'] = num_inlets
        self.gui_params['num_outlets'] = num_outlets
        self.gui_params['dsp_inlets'] = self.dsp_inlets
        self.gui_params['dsp_outlets'] = self.dsp_outlets

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
        need_conf = False
        if set(self.faust_initialized) != set(['inlets', 'outlets', 'params']):
            need_conf = True

        if resp_id == self.RESP_DSP_INLETS:
            self.faust_dsp_inlets = resp_value
            self.faust_initialized.append('inlets')
        elif resp_id == self.RESP_DSP_OUTLETS:
            self.faust_dsp_outlets = resp_value
            self.faust_initialized.append('outlets')
        elif resp_id == self.RESP_PARAM:
            if resp_value not in self.faust_params:
                self.faust_params.append(resp_value)
            self.faust_initialized.append('params')

        inlets = max(1, self.faust_dsp_inlets + len(self.faust_params))
        prev_inlets = len(self.inlets)
        self.resize(
            inlets,
            self.faust_dsp_outlets
        )
        if (
            len(self.dsp_inlets) != self.faust_dsp_inlets
            or len(self.dsp_outlets) != self.faust_dsp_outlets
            or inlets != prev_inlets
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
