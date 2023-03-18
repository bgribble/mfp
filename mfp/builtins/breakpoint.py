#! /usr/bin/env python
'''
breakpoint.py: [bp] builting for step execution

Copyright (c) 2023 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp
from mfp.bang import Bang, Uninit


class Breakpoint(Processor):
    doc_tooltip_obj = "Break execution and enter step execution mode"
    doc_tooltip_inlet = ["Inlet"]
    doc_tooltip_outlet = [ "Outlet" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        self.enabled = True
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

    async def trigger(self):
        await self.patch.step_execute_start()
        self.outlets[0] = self.inlets[0]


def register():
    MFPApp().register("bp", Breakpoint)

