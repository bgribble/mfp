#! /usr/bin/env python
'''
ampl.py:  Detector (peak/rms)

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp
from mfp import log


class Ampl(Processor):
    doc_tooltip_obj = "Compute RMS and peak amplitude"
    doc_tooltip_inlet = [ "Input signal" ]
    doc_tooltip_outlet = [ "RMS amplitude", "Peak amplitude" ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 1, 2, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)

        self.dsp_inlets = [0]
        self.dsp_outlets = [0, 1]

    async def setup(self):
        await self.dsp_init("ampl~")

    async def trigger(self):
        if isinstance(self.inlets[0], dict):
            for param, val in self.inlets[0].items():
                try:
                    await self.dsp_setparam(param, float(val))
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    log.debug("ampl~: Error setting param", param, "to", type(val), str(val))
                    log.debug("ampl~: Exception:", str(e))
                    self.error(tb)

def register():
    MFPApp().register("ampl~", Ampl)
