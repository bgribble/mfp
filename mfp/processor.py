#! /usr/bin/env python2.6
'''
processor.py: Parent class of all processors

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from .dsp_slave import DSPObject
from .method import MethodCall
from .bang import Uninit
from .scope import LexicalScope

from . import log


class Processor (object):
    CTOR = 0 
    READY = 1 
    ERROR = 2
    display_type = 'processor'
    hot_inlets = [0]

    def __init__(self, inlets, outlets, init_type, init_args,
                 patch, scope, name):
        from .main import MFPApp
        self.init_type = init_type
        self.init_args = init_args
        self.obj_id = MFPApp().remember(self)

        self.inlets = [Uninit] * inlets
        self.outlets = [Uninit] * outlets
        self.outlet_order = range(outlets)
        self.status = Processor.CTOR
        self.name = None
        self.patch = None
        self.scope = None
        self.osc_pathbase = None
        self.osc_methods = []

        self.gui_created = False
        self.do_onload = True 

        # gui_params are passed back and forth to the UI process
        # if previously-initialized by the child class, leave alone
        if not hasattr(self, "gui_params"):
            self.gui_params = {}

        defaults = dict(obj_id=self.obj_id, name=name,
                        initargs=self.init_args, display_type=self.display_type,
                        num_inlets=inlets, num_outlets=outlets)

        for k, v in defaults.items():
            if k not in self.gui_params:
                self.gui_params[k] = v 

        # dsp_inlets and dsp_outlets are the processor inlet/outlet numbers
        # of the ordinal inlets/outlets of the DSP object.
        # for example dsp_outlets = [2] means processor outlet 2
        # corresponds to outlet 0 of the underlying DSP object
        self.dsp_obj = None
        self.dsp_inlets = []
        self.dsp_outlets = []

        self.connections_out = [[] for r in range(outlets)]
        self.connections_in = [[] for r in range(inlets)]

        if patch is not None:
            self.assign(patch, scope, name)

    def info(self):
        log.debug("Object info: obj_id=%d, name=%s, init_type=%s, init_args=%s"
                  % (self.obj_id, self.name, self.init_type, self.init_args))
        return True

    def call_onload(self, value=True): 
        self.do_onload = value 

    def onload(self):
        pass 

    def assign(self, patch, scope, name):
        if self.patch is not None and self.scope is not None and self.name is not None:
            self.patch.unbind(self.name, self.scope)

        self.name = name or "%s_%s" % (self.init_type, str(self.obj_id))
        self.gui_params["name"] = self.name 

        if self.patch is None or self.patch != patch:
            if self.patch:
                self.patch.remove(self)
            self.patch = patch
            self.patch.add(self)

        if scope is not None:
            self.scope = scope
        else:
            self.scope = self.patch.default_scope

        self.patch.bind(self.name, self.scope, self)
        self.osc_init()

    def rename(self, new_name):
        self.assign(self.patch, self.scope, new_name)

    def rescope(self, new_scope):
        if isinstance(new_scope, LexicalScope):
            self.assign(self.patch, new_scope, self.name)
        else:
            self.assign(self.patch, self.patch.scopes.get(new_scope), self.name)

    def osc_init(self):
        from .main import MFPApp

        def handler(path, args, types, src, data):
            if types[0] == 's':
                self.send(self.patch.parse_obj(args[0]), inlet=data)
            else:
                self.send(args[0], inlet=data)

        if MFPApp().osc_mgr is None:
            return

        if self.patch is None:
            patchname = "default"
        else:
            patchname = self.patch.name

        pathbase = "/mfp/%s/%s" % (patchname, self.name)
        o = MFPApp().osc_mgr

        if self.osc_pathbase is not None and self.osc_pathbase != pathbase:
            for m in self.osc_methods:
                o.del_method(m, None)
            self.osc_methods = []
        self.osc_pathbase = pathbase

        for i in range(len(self.inlets)):
            path = "%s/%s" % (pathbase, str(i))
            if path not in self.osc_methods:
                o.add_method(path, 's', handler, i)
                o.add_method(path, 'b', handler, i)
                # o.add_method(path, 'i', handler, i)
                o.add_method(path, 'f', handler, i)
            self.osc_methods.append(path)

    def dsp_init(self, proc_name, **params):
        self.dsp_obj = DSPObject(self.obj_id, proc_name, len(self.dsp_inlets),
                                 len(self.dsp_outlets), params)
        self.gui_params['dsp_inlets'] = self.dsp_inlets
        self.gui_params['dsp_outlets'] = self.dsp_outlets

    def dsp_reset(self):
        self.dsp_obj.reset()

    def dsp_setparam(self, param, value):
        self.dsp_obj.setparam(param, value)

    def dsp_getparam(self, param, value):
        return self.dsp_obj.getparam(param, value)

    def delete(self):
        from .main import MFPApp
        if hasattr(self, "patch") and self.patch is not None:
            self.patch.unbind(self.name, self.scope)
            self.patch.remove(self)

        if hasattr(self, "osc_pathbase") and self.osc_pathbase is not None:
            for m in self.osc_methods:
                MFPApp().osc_mgr.del_method(m, 's')
                MFPApp().osc_mgr.del_method(m, 'b')
                MFPApp().osc_mgr.del_method(m, 'f')

            self.osc_methods = []
            self.osc_pathbase = None

        if hasattr(self, "connections_out"):
            outport = 0
            for c in self.connections_out:
                for tobj, tport in c:
                    self.disconnect(outport, tobj, tport)
                outport += 1

        if hasattr(self, "connections_in"):
            inport = 0
            for c in self.connections_in:
                for tobj, tport in c:
                    tobj.disconnect(tport, self, inport)
                inport += 1

        if hasattr(self, "dsp_obj") and self.dsp_obj is not None:
            self.dsp_obj.delete()

        MFPApp().forget(self)

    def resize(self, inlets, outlets):
        if inlets > len(self.inlets):
            newin = inlets - len(self.inlets)
            self.inlets += [Uninit] * newin
            self.connections_in += [[] for r in range(newin)]
        else:
            for inlet in range(inlets, len(self.inlets)):
                for tobj, tport in self.connections_in[inlet]:
                    tobj.disconnect(tport, self, inlet)
            self.inlets[inlets:] = []

        if outlets > len(self.outlets):
            newout = outlets - len(self.outlets)
            self.outlets += [Uninit] * newout
            self.connections_out += [[] for r in range(newout)]
        else:
            for outlet in range(outlets, len(self.outlets)):
                for tobj, tport in self.connections_out[outlet]:
                    self.disconnect(outlet, tobj, tport)
            self.outlets[outlets:] = []
            self.connections_out[outlets:] = []
        self.outlet_order = range(len(self.outlets))

        self.gui_params['num_inlets'] = inlets
        self.gui_params['num_outlets'] = outlets

        if self.gui_created:
            MFPApp().gui_cmd.configure(self.obj_id, self.gui_params)

    def connect(self, outlet, target, inlet):
        # is this a DSP connection?
        if outlet in self.dsp_outlets:
            self.dsp_obj.connect(self.dsp_outlets.index(outlet),
                                 target.obj_id, target.dsp_inlets.index(inlet))

        existing = self.connections_out[outlet]
        if (target, inlet) not in existing:
            existing.append((target, inlet))

        existing = target.connections_in[inlet]
        if (self, outlet) not in existing:
            existing.append((self, outlet))
        return True

    def disconnect(self, outlet, target, inlet):
        # is this a DSP connection?
        if outlet in self.dsp_outlets:
            self.dsp_obj.disconnect(self.dsp_outlets.index(outlet),
                                    target.obj_id, target.dsp_inlets.index(inlet))

        existing = self.connections_out[outlet]
        if (target, inlet) in existing:
            existing.remove((target, inlet))

        existing = target.connections_in[inlet]
        if (self, outlet) in existing:
            existing.remove((self, outlet))
        return True

    def send(self, value, inlet=0):
        try:
            work = self._send(value, inlet)
            while len(work):
                w_target, w_val, w_inlet = work[0]
                work[:1] = w_target._send(w_val, w_inlet)
        except:
            log.debug("send failed:", self, value, inlet)
            import traceback
            tb = traceback.format_exc()
            self.error(tb)

    def _send(self, value, inlet=0):
        work = []
        if inlet >= 0:
            self.inlets[inlet] = value

        if inlet in self.hot_inlets or inlet == -1:
            self.outlets = [Uninit] * len(self.outlets)
            if inlet == -1:
                self.dsp_response(value[0], value[1])
            elif isinstance(value, MethodCall):
                self.method(value, inlet)
            else:
                self.trigger()
            output_pairs = zip(self.connections_out, self.outlets)

            for conns, val in [output_pairs[i] for i in self.outlet_order]:
                if val is not Uninit:
                    for target, inlet in conns:
                        work.append((target, val, inlet))
        try:
            if inlet in self.dsp_inlets:
                self.dsp_obj.setparam("_sig_" + str(inlet), float(value))
        except (TypeError, ValueError):
            pass

        return work

    def parse_args(self, pystr):
        if self.patch:
            return self.patch.parse_args(pystr)
        else:
            from .evaluator import Evaluator
            e = Evaluator()
            return e.parse_args(pystr)

    def parse_obj(self, pystr):
        if self.patch:
            return self.patch.parse_obj(pystr)
        else:
            from .evaluator import Evaluator
            e = Evaluator()
            return e.parse_args(pystr)

    def method(self, message, inlet):
        '''Default method handler ignores which inlet the message was received on'''
        message.call(self)
        self.inlets[inlet] = Uninit

    def error(self, tb=None):
        self.status = Processor.ERROR
        print "Error:", self
        if tb:
            print tb

    def create_gui(self):
        from .main import MFPApp
        MFPApp().gui_cmd.create(self.init_type, self.init_args, self.obj_id,
                                self.gui_params)
        self.gui_created = True

    def delete_gui(self):
        from .main import MFPApp
        MFPApp().gui_cmd.delete(self.obj_id)
        self.gui_created = False

    def load(self, paramdict):
        # Override for custom load behavior
        pass

    def mark_ready(self):
        self.status = Processor.READY

    # save/restore helper
    def save(self):
        oinfo = {}
        oinfo['type'] = self.init_type
        oinfo['initargs'] = self.init_args
        oinfo['name'] = self.name
        oinfo['do_onload'] = self.do_onload
        oinfo['gui_params'] = self.gui_params
        conn = []
        for c in self.connections_out:
            conn.append([(t[0].obj_id, t[1]) for t in c])
        oinfo['connections'] = conn
        return oinfo

