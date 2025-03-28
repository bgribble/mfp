#! /usr/bin/env python 
'''
loadbang.py -- on-load message emitter 

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor 
from ..bang import Bang, Uninit 
from ..mfp_app import MFPApp
from mfp import log

class LoadBang (Processor):
    doc_tooltip_obj = "Emit a Bang message on patch load"

    def __init__(self, init_type, init_args, patch, scope, name, defs=None): 
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name, defs)

    async def trigger(self):
        self.outlets[0] = self.inlets[0]
        self.inlets[0] = Uninit

    async def onload(self, phase):
        if phase == 1:
            await self.send(Bang)

def register():
    MFPApp().register("loadbang", LoadBang)
