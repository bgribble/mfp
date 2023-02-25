#! /usr/bin/env python
'''
p_noise.py:  Builtin noise

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp


class Noise(Processor):
    doc_tooltip_obj = "Generate white noise"

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 0, 1, init_type, init_args, patch, scope, name)

        self.dsp_outlets = [0]

    async def setup(self):
        await self.dsp_init("noise~")

    async def trigger(self):
        pass


def register():
    MFPApp().register("noise~", Noise)
