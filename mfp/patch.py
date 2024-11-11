#! /usr/bin/env python
'''
patch.py
Patch class and methods

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import os

from .processor import Processor, AsyncOutput
from .evaluator import Evaluator
from .scope import LexicalScope
from .bang import Uninit, Unbound
from .utils import TaskNibbler
from .step_debugger import StepDebugger

from mfp import log


class Patch(Processor):

    EXPORT_LAYER = "Interface"
    display_type = "patch"
    default_context = None

    task_nibbler = None

    def __init__(self, init_type, init_args, patch, scope, name, context=None):
        Processor.__init__(self, 1, 0, init_type, init_args, patch, scope, name)
        if context is None:
            if patch is None:
                self.context = self.default_context
            else:
                self.context = patch.context
        else:
            self.context = context

        if not Patch.task_nibbler:
            Patch.task_nibbler = TaskNibbler()

        self.file_origin = None

        self.objects = {}
        self.scopes = {'__patch__': LexicalScope('__patch__')}
        self.default_scope = self.scopes['__patch__']
        self.evaluator = Evaluator()

        self.inlet_objects = []
        self.outlet_objects = []
        self.dispatch_objects = []

        self.step_debugger = StepDebugger()

        self.init_bindings()
        self.parsed_initargs, self.parsed_kwargs = self.parse_args(init_args)

        self.gui_params['layers'] = []
        self.gui_params['dsp_context'] = self.context.context_name if self.context else ""

        if patch is None:
            self.gui_params['top_level'] = True
        else:
            self.gui_params['top_level'] = False

    async def bp(self):
        await self.step_execute_start(self, "@bp message to patch")

    async def step_execute_start(self, target, message):
        if self.step_debugger.enabled:
            return
        await self.step_debugger.enable(target)
        await self.step_debugger.show_banner(message)
        await self.step_debugger.show_prompt()

    async def step_execute_stop(self):
        if not self.step_debugger.enabled:
            return
        self.step_debugger.disable()
        await self.step_debugger.show_leave()

    def init_bindings(self):
        from .mfp_app import MFPApp
        self.default_scope.bind("self", self)
        self.default_scope.bind("patch", self)
        self.default_scope.bind("app", MFPApp())

    def args(self, index=None):
        if index is None:
            return self.parsed_initargs
        elif self.parsed_initargs is None or index >= len(self.parsed_initargs):
            return Uninit
        else:
            return self.parsed_initargs[index]

    def kwargs(self, name=None):
        if name is None:
            return self.parsed_kwargs
        else:
            return self.parsed_kwargs.get(name, Uninit)

    def ping(self):
        log.debug("ping:", self.name)

    #############################
    # name management
    #############################

    def bind(self, name, scope, obj):
        if isinstance(scope, Patch):
            scope = scope.scopes['__patch__']
        return scope.bind(name, obj)

    def unbind(self, name, scope):
        exists, val = scope.query(name)
        if exists:
            scope.unbind(name)

    def resolve(self, name, scope=None):
        found = False
        obj = False

        if isinstance(scope, LexicalScope):
            found, obj = scope.query(name)

        if (not found) and scope is not None and scope in self.scopes:
            s = self.scopes.get(scope)
            found, obj = s.query(name)

        if (not found) and name in self.scopes:
            found = True
            obj = self.scopes.get(name)

        if not found:
            found, obj = self.default_scope.query(name)

        if found:
            return obj
        else:
            return Unbound

    def add_scope(self, name):
        if name not in self.scopes:
            self.scopes[name] = LexicalScope(name)
        return self.scopes[name]

    def del_scope(self, name):
        del self.scopes[name]

    def rename(self, new_name):
        from .mfp_app import MFPApp
        if new_name == self.name:
            return
        else:
            oldname = self.name
            Processor.rename(self, new_name)
            if self.patch is None and oldname in MFPApp().patches:
                del MFPApp().patches[oldname]
                MFPApp().patches[new_name] = self

    #############################
    # evaluator
    #############################

    def parse_obj(self, argstring, **extra_bindings):
        '''
        Parse and evaluate a Python expression
        '''
        if argstring == '' or argstring is None:
            return None

        return Processor.parse_obj(self, argstring, **extra_bindings)

    def parse_args(self, argstring, **extra_bindings):
        '''
        Parse and evaluate a Python expression representing
        a function/method argument list (returns tuple of positional
        args followed by dictionary of keyword args)

        This uses a tacky trick to capture args and kwargs which
        will generate some odd backtraces on error
        '''

        if argstring == '' or argstring is None:
            return ((), {})

        return Processor.parse_args(self, argstring, **extra_bindings)

    #############################
    # patch contents management
    #############################
    async def trigger(self):
        inlist = list(range(len(self.inlets)))
        inlist.reverse()

        for i in inlist:
            if self.inlets[i] is not Uninit:
                if isinstance(self.inlets[i], AsyncOutput):
                    await self.send(self.inlets[i])
                else:
                    await self.inlet_objects[i].send(self.inlets[i])
                self.inlets[i] = Uninit

        for o in range(len(self.outlets)):
            self.add_output(o, self.outlet_objects[o].outlets[0])
            self.outlet_objects[o].outlets[0] = Uninit

    async def method(self, message, inlet=0):
        if len(self.dispatch_objects):
            for d in self.dispatch_objects:
                await d.send(message)
        else:
            await self.baseclass_method(message, inlet)

        for o in range(len(self.outlets)):
            self.add_output(o, self.outlet_objects[o].outlets[0])
            self.outlet_objects[o].outlets[0] = Uninit

    async def baseclass_method(self, message, inlet=0):
        await Processor.method(self, message, inlet)

    def add(self, obj):
        if obj.obj_id in self.objects:
            return

        self.objects[obj.obj_id] = obj
        if obj.init_type in ('inlet', 'inlet~'):
            num = obj.inletnum
            if num >= len(self.inlet_objects):
                self.inlet_objects.extend([None] * (num - len(self.inlet_objects) + 1))
            self.inlet_objects[num] = obj
            self.resize(len(self.inlet_objects), len(self.outlet_objects))

            if obj.init_type == 'inlet~':
                self.dsp_inlets = [
                    p[0] for p in enumerate(self.inlet_objects)
                    if p[1] and p[1].init_type == 'inlet~'
                ]
                self.gui_params['dsp_inlets'] = self.dsp_inlets

        elif obj.init_type in ('outlet', 'outlet~'):
            num = obj.outletnum
            if num >= len(self.outlet_objects):
                self.outlet_objects.extend([None] * (num - len(self.outlet_objects) + 1))
            self.outlet_objects[num] = obj
            self.resize(len(self.inlet_objects), len(self.outlet_objects))

            if obj.init_type == 'outlet~':
                self.dsp_outlets = [
                    p[0] for p in enumerate(self.outlet_objects)
                    if p[1] and p[1].init_type == 'outlet~'
                ]
                self.gui_params['dsp_outlets'] = self.dsp_outlets

        elif obj.init_type == 'dispatch':
            self.dispatch_objects.append(obj)

    def remove(self, obj):
        try:
            if obj.scope is not None and obj.name is not None:
                self.unbind(obj.name, obj.scope)
            obj.patch = None
            del self.objects[obj.obj_id]
        except KeyError:
            log.error(f"Error deleting obj {obj}, can't find key {obj.obj_id}, continuing")
            log.debug(f"obj info: {obj.name} {obj.init_type} {obj.init_args} deleted={obj.status == obj.DELETED}")

        try:
            self.inlet_objects.remove(obj)
            self.dsp_inlets = [
                p[0] for p in enumerate(self.inlet_objects)
                if p[1] and p[1].init_type == 'inlet~'
            ]
            self.gui_params['dsp_inlets'] = self.dsp_inlets
        except ValueError:
            pass

        try:
            self.outlet_objects.remove(obj)
            self.dsp_outlets = [
                p[0] for p in enumerate(self.outlet_objects)
                if p[1] and p[1].init_type == 'outlet~'
            ]
            self.gui_params['dsp_outlets'] = self.dsp_outlets
        except ValueError:
            pass

        try:
            self.dispatch_objects.remove(obj)
        except ValueError:
            pass

    async def connect(self, outlet, target, inlet, show_gui=True):
        from .mfp_app import MFPApp

        async def _patch_connect_retry(args):
            rv = await Processor.connect(*args)
            return rv

        # we may have to retry this if some outlets are made in
        # the loadbang
        initial = await Processor.connect(self, outlet, target, inlet, show_gui)
        if not initial:
            Patch.task_nibbler.add_task(
                lambda args: _patch_connect_retry(args), 20,
                [self, outlet, target, inlet, show_gui]
            )
        return True

    ############################
    # DSP inlet/outlet access
    ############################

    def dsp_inlet(self, inlet):
        try:
            return (self.inlet_objects[inlet].dsp_obj, 0)
        except IndexError:
            log.error("Programming error: asked for inlet '%d' in patch %s but it has %d"
                      % (inlet, self.name, len(self.inlet_objects)))
            return (None, 0)

    def dsp_outlet(self, outlet):
        try:
            return (self.outlet_objects[outlet].dsp_obj, 0)
        except IndexError:
            log.error("Programming error: asked for outlet '%d' in patch %s but it has %d"
                      % (outlet, self.name, len(self.outlet_objects)))
            return (None, 0)

    ############################
    # load/save
    ############################

    @classmethod
    def register_file(cls, filename):
        from .mfp_app import MFPApp

        async def factory(init_type, init_args, patch, scope, name, context=None):
            p = Patch(init_type, init_args, patch, scope, name, context)
            await p._load_file(filename)
            p.init_type = init_type
            return p

        basefile = os.path.basename(filename)
        parts = os.path.splitext(basefile)

        log.debug("Patch.register_file: registering type '%s' from file '%s'"
                  % (parts[0], filename))
        MFPApp().register(parts[0], factory)
        return (parts[0], factory)

    async def create_gui(self, **kwargs):
        from .mfp_app import MFPApp

        if MFPApp().no_gui:
            return False
        if self.gui_created:
            return True

        # create the basic element info
        self.update_export_bounds()
        await Processor.create_gui(self, **kwargs)

        if self.gui_params.get("top_level"):
            await MFPApp().gui_command.load_start()

            for oid, obj in list(self.objects.items()):
                if obj.display_type != "hidden":
                    await obj.create_gui()

            for oid, obj in self.objects.items():
                for srcport, connections in enumerate(obj.connections_out):
                    for dstobj, dstport in connections:
                        if (
                            obj.display_type not in (
                                "hidden", "sendvia", "sendsignalvia"
                            )
                            and dstobj.display_type not in (
                                "hidden", "recvvia", "recvsignalvia"
                            )
                        ):
                            await MFPApp().gui_command.connect(
                                obj.obj_id, srcport, dstobj.obj_id, dstport
                            )
            await MFPApp().gui_command.load_complete()
            await MFPApp().gui_command.select(self.obj_id)
        else:
            await self.create_export_gui()
        return True

    async def delete_gui(self):
        if not self.gui_created:
            return True

        for _, obj in self.objects.items():
            obj.gui_created = False

        await Processor.delete_gui(self)
        return True

    async def has_unsaved_changes(self):
        import copy
        if self.file_origin:
            oldjson = open(self.file_origin, 'r').read()
            saved_gui = copy.copy(self.gui_params)
            for k in ['num_inlets', 'num_outlets', 'obj_id', 'top_level']:
                if k in self.gui_params:
                    del self.gui_params[k]

            newjson = await self.json_serialize()
            self.gui_params = saved_gui

            # cdiff = difflib.context_diff(oldjson.split('\n'), newjson.split('\n'))

            if oldjson != newjson:
                log.warning("Unsaved changes in '%s'" % self.name, "(%s)" % self.file_origin)
                return True
        elif len(self.objects):
            log.warning("Unsaved changes in new patch '%s'" % self.name)
            return True
        return False

    async def save_file(self, filename):
        basefile = os.path.basename(filename)
        parts = os.path.splitext(basefile)

        self.update_export_bounds()
        self.init_type = parts[0]

        if os.path.isfile(filename):
            os.rename(filename, filename+'~')
        log.debug(f"Saving patch to {filename}")
        with open(filename, "w") as savefile:
            savefile.write(await self.json_serialize())

        self.file_origin = filename

    async def save_lv2(self, plugname, filename):
        import os.path
        log.debug("save_lv2: %s, %s" % (plugname, filename))
        plugpath = self.lv2_create_dir(plugname)
        ttlpath = os.path.join(plugpath, "manifest.ttl")
        self.lv2_write_ttl(ttlpath, plugname, filename)
        patchpath = os.path.join(plugpath, filename)
        await self.save_file(patchpath)

    async def _load_file(self, filename):
        from .mfp_app import MFPApp
        from .utils import splitpath

        searchpath = MFPApp().searchpath or ""
        searchdirs = splitpath(searchpath)
        jsdata = None
        filepath = None

        for d in searchdirs:
            path = os.path.join(d, filename)
            try:
                os.stat(path)
                jsdata = open(path, 'r').read()
                filepath = path
            except OSError:
                pass

        if jsdata is not None:
            await self.json_deserialize(jsdata)
            self.file_origin = filepath
            self.gui_params["dsp_context"] = self.context.context_name
            if not MFPApp().no_onload:
                await self._run_onload(list(self.objects.values()))

    async def _run_onload(self, objects):
        from .mfp_app import MFPApp
        for phase in (0, 1):
            for obj in objects:
                try:
                    if obj.do_onload:
                        await obj.onload(phase)
                except Exception as e:
                    log.error(f"Problem initializing {obj.scope.name}.{obj.name}: {e}")
                    log.debug_traceback(e)

        self.update_export_bounds()

        if MFPApp().gui_command:
            await MFPApp().gui_command.load_complete()
        return True

    def obj_is_exportable(self, obj):
        if (obj.gui_params.get('is_export')
            or (obj.gui_params.get("layername") == Patch.EXPORT_LAYER
                and obj.gui_params.get("no_export", False) is not True
                and "display_type" in obj.gui_params
                and (obj.gui_params.get("display_type") not in
                     ("sendvia", "recvvia", "sendsignalvia", "recvsignalvia")))):
            return True
        else:
            return False

    def update_export_bounds(self):
        min_x = min_y = max_x = max_y = None

        for obj_id, obj in self.objects.items():
            if self.obj_is_exportable(obj):
                x = (obj.gui_params.get("position_x")
                     - obj.gui_params.get('export_offset_x', 0))
                y = (obj.gui_params.get("position_y")
                     - obj.gui_params.get('export_offset_y', 0))
                w = obj.gui_params.get("width")
                h = obj.gui_params.get("height")

                if min_x is None or (x < min_x):
                    min_x = x
                if min_y is None or (y < min_y):
                    min_y = y
                if max_x is None or (x+w > max_x):
                    max_x = x+w
                if max_y is None or (y+h > max_y):
                    max_y = y+h

        x = y = w = h = None
        if None not in (min_x, min_y, max_x, max_y):
            x = min_x
            y = min_y
            w = max_x - min_x + 2
            h = max_y - min_y + 2

        self.conf(export_x=x, export_y=y, export_w=w, export_h=h,
                  width=max(self.gui_params.get('width') or 0,
                            self.gui_params.get('export_w') or 0),
                  height=max(self.gui_params.get('height') or 0,
                             (self.gui_params.get('export_h') or 0) + 20))

    async def create_export_gui(self):
        from .mfp_app import MFPApp
        # non-toplevel Patch means show the Export UI layer only
        await MFPApp().gui_command.load_start()
        for oid, obj in list(self.objects.items()):
            if self.obj_is_exportable(obj):
                await obj.create_gui(is_export=True)
        await MFPApp().gui_command.load_complete()

    async def delete(self):
        from .mfp_app import MFPApp
        if self.name in MFPApp().patches and MFPApp().patches[self.name] == self:
            del MFPApp().patches[self.name]

        if self.gui_created:
            await self.delete_gui()

        # first pass: everything but inlets/outlets
        to_delete = self.objects.values()
        for obj in list(to_delete):
            await obj.delete()

        if self.step_debugger:
            self.step_debugger.disable()
            self.step_debugger = None

        await Processor.delete(self)

# load extension methods
from . import patch_json  # noqa
from . import patch_lv2  # noqa
from . import patch_clonescope  # noqa
