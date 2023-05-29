#! /usr/bin/env python
'''
patch_info.py
PatchInfo class capturing display information for a patch

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..gui_main import MFPGUI
from .layer import Layer

class PatchInfo (object):
    display_type = "patch"

    def __init__(self, window, x, y):
        self.stage = window
        self.obj_id = None
        self.obj_type = None
        self.obj_args = None
        self.obj_name = None
        self.context_name = None
        self.deletable = True
        self.last_filename = None
        self.layers = []
        self.scopes = []

        self.stage.app.add_patch(self)
        self.stage.layer_view.insert(self, None)
        self.stage.object_view.insert(self, None)

    def update(self):
        pass

    def has_scope(self, scope_name):
        # FIXME - needs scopes for objects in scopes-not-default-for-layers
        return scope_name in [l.scope for l in self.layers]

    def synced_params(self):
        return dict(display_type=self.display_type, name=self.obj_name,
                    layers=[(l.name, l.scope) for l in self.layers])

    def send_params(self, **extras):
        prms = self.synced_params()
        for k, v in extras.items():
            prms[k] = v
        if self.obj_id is not None:
            MFPGUI().mfp.set_params.sync(self.obj_id, prms)

    def find_layer(self, layer):
        for l in self.layers:
            if l.name == layer:
                return l
        return None

    def get_params(self):
        return MFPGUI().mfp.get_params.sync(self.obj_id)

    def configure(self, params):
        self.num_inlets = params.get("num_inlets")
        self.num_outlets = params.get("num_outlets")
        self.dsp_inlets = params.get("dsp_inlets")
        self.dsp_outlets = params.get("dsp_outlets")
        self.obj_name = params.get("name")
        self.context_name = params.get("dsp_context")
        self.deletable = params.get("deletable", True)

        layers = params.get("layers", [])
        newlayers = []
        for name, scope in layers:
            layer = self.find_layer(name)
            if layer is None:
                layer = Layer(self.stage, self, name, scope)
            newlayers.append(layer)
        self.layers = newlayers

        self.scopes = []
        for layer in self.layers:
            if not self.stage.layer_view.in_tree(layer):
                self.stage.layer_view.insert(layer, self)
            if layer.scope not in self.scopes:
                self.scopes.append(layer.scope)

        for s in self.scopes:
            if not self.stage.object_view.in_tree((s, self)):
                self.stage.object_view.insert((s, self), self)

        self.stage.refresh(self)

    def delete(self):
        # delete all the processor elements
        for layer in self.layers:
            to_delete = [o for o in layer.objects]
            for o in to_delete:
                o.delete()
            layer.hide()
            del layer.group
            layer.group = None

        # remove the patch from layers and objects lists
        self.stage.object_view.remove(self)
        self.stage.layer_view.remove(self)

        # last, delete the patch on the control side
        if self.obj_id is not None:
            MFPGUI().mfp.delete.sync(self.obj_id)
            self.obj_id = None

    def command(self, action, data):
        pass
