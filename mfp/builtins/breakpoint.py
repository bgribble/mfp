#! /usr/bin/env python
'''
breakpoint.py: [bp] builting for step execution

Copyright (c) 2023 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp
from mfp.bang import Uninit


class Breakpoint(Processor):
    """
    [bp]

    Enter step mode on any input

    input 0: pass through/trigger input
    input 1: if True (default), break on next input, else do not
    """
    doc_tooltip_obj = "Break execution and enter step execution mode"
    doc_tooltip_inlet = ["Trigger/passthru", "Enable"]
    doc_tooltip_outlet = ["Outlet"]

    def __init__(self, init_type, init_args, patch, scope, name):
        self.enabled = True

        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)

    async def trigger(self):
        if self.inlets[1] != Uninit:
            self.enabled = bool(self.inlets[1])

        if self.enabled:
            await self.patch.step_execute_start(f"Breakpoint in processor {self.name}")

        self.outlets[0] = self.inlets[0]


def register():
    MFPApp().register("bp", Breakpoint)
