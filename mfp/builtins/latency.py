#! /usr/bin/env python
'''
latency.py:  Report app DSP latency changes 

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp
from .. import Bang

class Latency(Processor):
    doc_tooltip_obj = "Report DSP latency changes (in milliseconds)"
    doc_tooltip_outlet = ["Input latency", "Output latency" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 2, init_type, init_args, patch, scope, name)

        self.callback = MFPApp().signal_listen("latency", self._latency_cb)
        self.outlet_order = [1, 0]

    def _latency_cb(self, app, signal):
        self.send(Bang)

    async def delete(self):
        if self.callback is not None:
            MFPApp().signal_unlisten(self.callback)
        await Processor.delete(self)

    async def trigger(self):
        in_latency, out_latency = self.patch.context.get_latency()
        self.outlets[0] = in_latency
        self.outlets[1] = out_latency  


def register():
    MFPApp().register("latency", Latency)
