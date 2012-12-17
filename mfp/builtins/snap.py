#! /usr/bin/env python
'''
p_snap.py: Grab a single sample from the block

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp
from .. import Bang
from .. import log


class Snap(Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            self.retrigger = initargs[0]
        else:
            self.retrigger = 0

        self.dsp_inlets = [0]
        self.dsp_init("snap~")
        self.dsp_setparam("retrigger", self.retrigger)
        if self.retrigger > 0:
            self.dsp_setparam("trigger", 1.0)

    def trigger(self):
        if self.inlets[0] is Bang:
            self.dsp_setparam("trigger", 1.0)
        elif self.inlets[0] is True:
            self.dsp_setparam("retrigger", self.retrigger)
            self.dsp_setparam("trigger", 1.0)
        elif self.inlets[0] is False:
            self.dsp_setparam("retrigger", 0.0)
        elif isinstance(self.inlets[0], dict):
            for param, val in self.inlets[0].items():
                try:
                    self.dsp_setparam(param, float(val))
                except Exception, e:
                    log.debug("snap~: Error setting param", param, "to", type(val), str(val))
                    log.debug("snap~: Exception:", str(e))
        elif isinstance(self.inlets[0], (float, int)):
            self.dsp_setparam("_sig_0", float(self.inlets[0]))

    def dsp_response(self, resp_type, resp_value):
        self.outlets[0] = resp_value


def register():
    MFPApp().register("snap~", Snap)
