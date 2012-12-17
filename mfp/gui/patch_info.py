#! /usr/bin/env python
'''
patch_info.py
PatchInfo class capturing display information for a patch

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..gui_slave import MFPGUI
from .patch_layer import PatchLayer


class PatchInfo (object):
    display_type = "patch"

    def __init__(self, window, x, y):
        print "Creating PatchInfo"
        self.stage = window
        self.obj_id = None
        self.obj_type = None
        self.obj_args = None
        self.obj_name = None
        self.layers = []

        self.stage.add_patch(self)

    def has_scope(self, scope_name):
        return scope_name in [l.scope for l in self.layers]

    def send_params(self, **extras):
        prms = dict(display_type=self.display_type,
                    layers=[(l.name, l.scope) for l in self.layers])
        for k, v in extras.items():
            prms[k] = v
        print "PatchInfo send_params:", self.obj_id, prms
        if self.obj_id is not None:
            MFPGUI().mfp.set_params(self.obj_id, prms)

    def get_params(self):
        return MFPGUI().mfp.get_params(self.obj_id)

    def configure(self, params):
        print "PatchInfo configure:", self.obj_id, params
        self.num_inlets = params.get("num_inlets")
        self.num_outlets = params.get("num_outlets")
        self.dsp_inlets = params.get("dsp_inlets")
        self.dsp_outlets = params.get("dsp_outlets")
        self.obj_name = params.get("name")

        self.layers = []
        layers = params.get("layers", [])
        for name, scope in layers:
            l = PatchLayer(self.stage, self, name, scope)
            self.layers.append(l)
        self.stage.layer_store_update()
        self.stage.layer_selection_update()

    def command(self, action, data):
        pass
