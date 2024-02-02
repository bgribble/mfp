#! /usr/bin/env python
'''
vcq12.py: 12TET quantizer for V/oct control voltages

Copyright (c) 2020 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit


class VCQ12(Processor):
    doc_tooltip_obj = "Quantize to 12TET semitones"
    doc_tooltip_inlet = [
        "Signal input", "Map of quantized tones"
    ]

    maps = {
        'major': [
            (0, 0), (1, 0), (2, 2), (3, 2),
            (4, 4), (5, 5), (6, 5), (7, 7),
            (8, 7), (9, 9), (10, 9), (11, 11),
        ],
        'minor': [
            (0, 0), (1, 0), (2, 2), (3, 2),
            (4, 4), (5, 5), (6, 5), (7, 7),
            (8, 8), (9, 8), (10, 10), (11, 10),
        ],
        'semitone': [
            (0, 0), (1, 1), (2, 2), (3, 3),
            (4, 4), (5, 5), (6, 6), (7, 7),
            (8, 8), (9, 9), (10, 10), (11, 11),
        ],
    }

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        if len(initargs):
            self.mapname = initargs[0]
        else:
            self.mapname = "semitone"

        self.map = self.maps.get(self.mapname)
        self.hot_inlets = [0, 1]
        self.dsp_inlets = [0]
        self.dsp_outlets = [0]
        self.init_mapvals = [val for pair in self.map for val in pair]

    async def setup(self):
        await self.dsp_init("vcq12~", map=self.init_mapvals)

    async def trigger(self):
        if self.inlets[1] is not Uninit:
            self.mapname = self.inlets[1]
            self.map = self.maps.get(self.mapname, self.maps['semitone'])
            await self.dsp_setparam("map", [val for pair in self.map for val in pair])


def register():
    MFPApp().register("vcq12~", VCQ12)
