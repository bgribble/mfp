#! /usr/bin/env python
'''
patch_json.py
Methods to save and load JSON patch data

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import simplejson as json
from .patch import Patch
from .utils import extends
from . import log
from .rpc.request import ExtendedEncoder, extended_decoder_hook


@extends(Patch)
async def json_deserialize(self, json_data):
    from .scope import NaiveScope

    f = json.loads(json_data, object_hook=extended_decoder_hook)
    self.init_type = f.get('type')

    # don't swap Patch gui_params if this isn't a top-level patch
    if self.patch is None:
        self.gui_params = f.get('gui_params', {})
        self.gui_params['top_level'] = True
    else:
        # pick out a few things that we need
        gp = f.get('gui_params', {})
        for prm in ('num_inlets', 'num_outlets', 'export_x', 'export_y', 'export_w',
                    'export_h'):
            if prm in gp:
                self.gui_params[prm] = gp[prm]
        self.gui_params['top_level'] = False

    # reset params that need it
    self.gui_params["obj_id"] = self.obj_id
    self.gui_params["name"] = self.name

    # clear old objects
    for o in self.objects.values():
        await o.delete()
    self.objects = {}
    self.scopes = {}
    self.inlet_objects = []
    self.outlet_objects = []
    self.dispatch_objects = []

    # create new objects
    # dumb_scope will allow multiple objects with a name, we will resolve when
    # reloading scopes
    dumb_scope = NaiveScope()
    idmap = self.json_unpack_objects(f, dumb_scope)

    # load new scopes
    scopes = f.get("scopes", {})
    for scopename, bindings in scopes.items():
        s = self.add_scope(scopename)
        for name, oid in bindings.items():
            if name in ("self", "patch"):
                continue

            obj = idmap.get(oid)
            if obj is None:
                log.debug("Error in patch (object %d not found), continuing anyway" % oid)
            else:
                dumb_scope.unbind(obj.name)
                self.bind(name, s, obj)
                obj.scope = s
                obj.gui_params['scope'] = obj.scope.name

    self.default_scope = self.scopes.get('__patch__') or self.add_scope("__patch__")
    self.init_bindings()

    # failsafe -- add un-scoped objects to default scope
    for oid, obj in self.objects.items():
        if obj.scope is dumb_scope:
            dumb_scope.unbind(obj.name)
            self.bind(obj.name, self.default_scope, obj)
            obj.scope = self.default_scope

    # make connections
    await self.json_unpack_connections(f, idmap)

    inlets = len(self.inlet_objects)
    if not inlets:
        inlets = 1
    self.resize(inlets, len(self.outlet_objects))

    hot = f.get('hot_inlets')
    if hot is not None:
        self.hot_inlets = hot

    for oid, obj in self.objects.items():
        await obj.onload(-1)

@extends(Patch)
async def json_unpack_connections(self, data, idmap):
    from .mfp_app import MFPApp
    for oid, prms in data.get('objects', {}).items():
        oid = int(oid)
        conn = prms.get("connections", [])
        srcobj = idmap.get(oid)
        for outlet in range(0, len(conn)):
            connlist = conn[outlet]
            for c in connlist:
                dstobj = idmap.get(c[0])
                inlet = c[1]
                if dstobj is None:
                    print("Deserializing problem: can't make connection to", c[0])
                    print(prms)
                else:
                    await srcobj.connect(outlet, dstobj, inlet)

@extends(Patch)
async def json_unpack_objects(self, data, scope):
    from .mfp_app import MFPApp
    idmap = {}
    idlist = list(data.get('objects').keys())
    idlist.sort(key=lambda x: int(x))
    need_gui = []

    for oid in idlist:
        prms = data.get('objects')[oid]

        otype = prms.get('type')
        oargs = prms.get('initargs')
        oname = prms.get('name')

        newobj = await MFPApp().create(otype, oargs, self, scope, oname)
        newobj.patch = self
        newobj.load(prms)
        if self.gui_created:
            need_gui.append(newobj)

        idmap[int(oid)] = newobj

    # find mapping for self to catch vias
    defscope = data.get('scopes').get('__patch__')
    selfid = int(defscope.get("self") or "0")
    idmap[selfid] = self

    self.update_export_bounds()
    for obj in need_gui:
        await obj.create_gui()

    return idmap

@extends(Patch)
async def json_serialize(self):
    from .mfp_app import MFPApp
    f = {}
    f['type'] = self.init_type
    gprms = { k: v for k, v in self.gui_params.items()
              if k not in ['dsp_context'] }
    gprms['name'] = self.init_type
    f['gui_params'] = gprms
    f['hot_inlets'] = self.hot_inlets

    allobj = {}
    keys = list(self.objects.keys())
    keys.sort()
    for oid in keys:
        o = self.objects.get(oid)
        if o and (isinstance(o, MFPApp) or not o.save_to_patch):
            continue
        oinfo = await o.save()
        allobj[oid] = oinfo

    f['objects'] = allobj

    scopes = {}
    for scopename, scope in self.scopes.items():
        bindings = {}
        for objname, obj in scope.bindings.items():
            if not obj:
                log.warning("json_serialize: name", objname, "has no bound object")
                continue
            if obj and (isinstance(obj, MFPApp) or not obj.save_to_patch):
                continue
            bindings[objname] = obj.obj_id

        scopes[scopename] = bindings

    f['scopes'] = scopes
    return json.dumps(f, sort_keys=True, indent=4, cls=ExtendedEncoder)
