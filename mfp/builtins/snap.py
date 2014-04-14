#! /usr/bin/env python
'''
p_snap.py: Grab a single sample from the block

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp
from .. import Bang, Uninit
from .. import log


class Snap(Processor):
    doc_tooltip_obj = "Capture a single or periodic snapshot value of a signal"
    doc_tooltip_inlet = ["Signal to snapshot", 
                         "Snapshot interval (ms) (default: initarg 0)"]
    doc_tooltip_outlet = ["Value output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            self.retrigger = initargs[0]
        else:
            self.retrigger = 0

        self.dsp_inlets = [0]
        self.dsp_init("snap~")
        self.dsp_setparam("retrigger", self.retrigger)

    def trigger(self):
        if isinstance(self.inlets[1], (float, int)):
            self.retrigger = float(self.inlets[1])

        if self.inlets[0] is Bang:
            self.dsp_setparam("trigger", 1.0)
        elif self.inlets[0] is True:
            self.dsp_setparam("retrigger", self.retrigger)
            self.dsp_setparam("trigger", 1.0)
        elif self.inlets[0] is False:
            self.dsp_setparam("retrigger", 0.0)
        elif isinstance(self.inlets[0], dict):
            for param, val in self.inlets[1].items():
                try:
                    self.dsp_setparam(param, float(val))
                except Exception, e:
                    import traceback 
                    tb = traceback.format_exc()
                    log.debug("snap~: Error setting param", param, "to", type(val), str(val))
                    log.debug("snap~: Exception:", str(e))
                    self.error(tb)

    def dsp_response(self, resp_type, resp_value):
        self.outlets[0] = resp_value


def register():
    MFPApp().register("snap~", Snap)
