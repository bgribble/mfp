#! /usr/bin/env python
'''
patch_display.py
PatchDisplay class captures display information for a patch:
a subset of the layers and objects in the app window

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

from flopsy import Action, Store, mutates, reducer, saga
from mfp import log
from ..gui_main import MFPGUI
from .layer import Layer
from .param_info import ParamInfo, ListOfInt, CodeBlock, DictOfProperty


class PatchDisplay(Store):

    display_type = "patch"
    store_attrs = {
        'panel_mode': ParamInfo(label="Panel mode", param_type=bool)
    }

    def __init__(self, window, x, y, **kwargs):
        self.app_window = window
        self.obj_id = None
        self.obj_type = None
        self.obj_args = None
        self.obj_name = None
        self.context_name = None
        self.deletable = True
        self.last_filename = None
        self.layers = []
        self.scopes = []
        self.selected_layer = None
        self.display_info = kwargs.get('display_info')
        self.export_x = None
        self.export_y = None
        self.export_w = None
        self.export_h = None
        self.panel_mode = False

        super().__init__()

    @classmethod
    def get_factory(cls):
        return cls

    @classmethod
    def build(cls, *args, **kwargs):
        return cls.get_factory()(*args, **kwargs)

    async def update(self):
        pass

    def has_scope(self, scope_name):
        # FIXME - needs scopes for objects in scopes-not-default-for-layers
        return scope_name in [ll.scope for ll in self.layers]

    def synced_params(self):
        return dict(
            display_type=self.display_type,
            name=self.obj_name,
            layers=[(ll.name, ll.scope) for ll in self.layers],
            export_x=self.export_x,
            export_y=self.export_y,
            export_w=self.export_w,
            export_h=self.export_h,
            panel_mode=self.panel_mode,
        )

    def send_params(self, **extras):
        prms = self.synced_params()
        for k, v in extras.items():
            prms[k] = v
        if self.obj_id is not None:
            MFPGUI().async_task(MFPGUI().mfp.set_params(self.obj_id, prms))

    def find_layer(self, layer):
        for ll in self.layers:
            if ll.name == layer:
                return ll
        return None

    @saga("panel_mode")
    async def panel_mode_changed(self, action, state_diff, previous):
        if "panel_mode" not in state_diff:
            return
        all_obj = []
        for layer in self.layers:
            for obj in layer.objects:
                all_obj.append(obj)

        for obj in sorted(all_obj, key=lambda o: o.position_z):
            new_x, new_y, new_z = obj.calc_position()
            yield Action(obj, obj.SET_POSITION_X, dict(value=new_x))
            yield Action(obj, obj.SET_POSITION_Y, dict(value=new_y))
            yield Action(obj, obj.SET_POSITION_Z, dict(value=new_z))

    @mutates('panel_mode')
    async def configure(self, params):
        self.num_inlets = params.get("num_inlets")
        self.num_outlets = params.get("num_outlets")
        self.dsp_inlets = params.get("dsp_inlets")
        self.dsp_outlets = params.get("dsp_outlets")
        self.obj_name = params.get("name")
        self.context_name = params.get("dsp_context")
        self.deletable = params.get("deletable", True)

        self.export_x = params.get("export_x")
        self.export_y = params.get("export_y")
        self.export_w = params.get("export_w")
        self.export_h = params.get("export_h")

        self.panel_x = params.get("panel_x")
        self.panel_y = params.get("panel_y")
        self.panel_z = params.get("panel_z")

        if "panel_mode" in params:
            self.panel_mode = params.get("panel_mode")

        layers = params.get("layers", [])

        newlayers = []
        for name, scope in layers:
            layer = self.find_layer(name)
            if layer is None:
                layer = Layer.build(self.app_window, self, name, scope)
            newlayers.append(layer)
        self.layers = newlayers

        self.scopes = []
        for layer in self.layers:
            if layer.scope not in self.scopes:
                self.scopes.append(layer.scope)

        self.last_filename = self.last_filename or params.get("file_origin")
        if not self.display_info:
            self.app_window.add_patch(self, new_page=params.get("new_page", False))

        self.app_window.refresh(self)

    async def delete(self, delete_obj=True):
        if self.obj_id is None:
            return

        # delete all the processor elements
        for layer in self.layers:
            to_delete = [o for o in layer.objects]
            for o in to_delete:
                await o.delete(delete_obj=delete_obj)
            layer.hide()
            layer.delete()

        # last, delete the patch on the control side
        to_delete = self.obj_id
        self.obj_id = None
        if delete_obj and to_delete is not None:
            await MFPGUI().mfp.delete(to_delete)
