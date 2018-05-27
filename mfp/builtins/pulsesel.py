
#! /usr/bin/env python
'''
pulsesel.py: Select some pulses from a pulse train

Copyright (c) 2018 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp
from .. import Bang, Uninit


class PulseSel(Processor):
    doc_tooltip_obj = "Pulse train divider/selector"
    doc_tooltip_inlet = ["Signal input/reset",
                         "Period",
                         "Selection bitmask",
                         "Trigger threshold (default: 0.25)",
                        ]
    doc_tooltip_outlet = ["Signal output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 4, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        period = 2
        bitmask = 1
        thresh = 0.25

        if len(initargs) > 0:
            period = initargs[0]
        if len(initargs) > 1:
            bitmask = initargs[1]
        if len(initargs) > 2:
           thresh = initargs[2]

        self.dsp_inlets = [0]
        self.dsp_outlets = [0]
        self.dsp_init(
            "pulsesel~",
            bitmask=bitmask, period=period, threshold=thresh
        )

    def trigger(self):
        if self.inlets[0] is Bang:
            self.dsp_setparam("phase", float(0))
        elif self.inlets[0] is not Uninit:
            self.dsp_setparam("phase", phase)


def register():
    MFPApp().register("pulsesel~", PulseSel)
