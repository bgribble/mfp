#! /usr/bin/env python
'''
sendrcv.py: Bus/virtual wire objects.

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp
from .. import Bang, Uninit
from mfp import log


class Send (Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 0, init_type, init_args, patch, scope, name)

        self.dest_name = None
        self.dest_inlet = 0
        self.dest_obj = None

        initargs, kwargs = self.parse_args(init_args)
        if len(initargs) > 1:
            self.dest_inlet = initargs[1]
        if len(initargs):
            self.dest_name = initargs[0]

        self.gui_params["label"] = self.dest_name

    def method(self, message, inlet):
        self.trigger()

    def trigger(self):
        if self.inlets[1] is not Uninit:
            self.dest_name = self.inlets[1]
            self.gui_params["label"] = self.dest_name
            self.dest_obj = None
            self.inlets[1] = Uninit

        if self.dest_obj is None:
            self.dest_obj = MFPApp().resolve(self.dest_name, self)

        if self.dest_obj is not None:
            self.dest_obj.send(self.inlets[0], inlet=self.dest_inlet)


class Recv (Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        self.gui_params["label"] = self.name

        if len(initargs):
            self.rename(initargs[0])

    def trigger(self):
        self.outlets[0] = self.inlets[0]

    def rename(self, new_name):
        Processor.rename(self, new_name)
        self.gui_params["label"] = self.name

        if self.gui_created:
            MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)


def register():
    MFPApp().register("send", Send)
    MFPApp().register("recv", Recv)
    MFPApp().register("s", Send)
    MFPApp().register("r", Recv)
