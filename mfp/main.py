#! /usr/bin/env python
'''
main.py: main routine for mfp

Copyright (c) 2010-2012 Bill Gribble <grib@billgribble.com>
'''

import time

from .bang import Bang
from .patch import Patch
from .scope import LexicalScope
from .singleton import Singleton
from .interpreter import Interpreter
from .evaluator import Evaluator
from .processor import Processor

from .rpc_wrapper import RPCWrapper, rpcwrap
from .rpc_worker import RPCServer

from . import log

class MFPCommand(RPCWrapper):
    @rpcwrap
    def create(self, objtype, initargs, patch_name, scope_name, obj_name):
        patch = MFPApp().patches.get(patch_name)
        scope = patch.scopes.get(scope_name) or patch.default_scope

        obj = MFPApp().create(objtype, initargs, patch, scope, obj_name)
        if obj is None:
            return None
        return obj.gui_params

    @rpcwrap
    def connect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
        obj_1 = MFPApp().recall(obj_1_id)
        obj_2 = MFPApp().recall(obj_2_id)
        r = obj_1.connect(obj_1_port, obj_2, obj_2_port)
        return r

    @rpcwrap
    def disconnect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
        obj_1 = MFPApp().recall(obj_1_id)
        obj_2 = MFPApp().recall(obj_2_id)

        r = obj_1.disconnect(obj_1_port, obj_2, obj_2_port)
        return r

    @rpcwrap
    def send_bang(self, obj_id, port):
        obj = MFPApp().recall(obj_id)
        obj.send(Bang, port)
        return True

    @rpcwrap
    def send(self, obj_id, port, data):
        obj = MFPApp().recall(obj_id)
        obj.send(data, port)
        return True

    @rpcwrap
    def eval_and_send(self, obj_id, port, message):
        obj = MFPApp().recall(obj_id)
        obj.send(obj.parse_obj(message), port)
        return True

    @rpcwrap
    def delete(self, obj_id):
        obj = MFPApp().recall(obj_id)
        obj.delete()

    @rpcwrap
    def set_params(self, obj_id, params):
        obj = MFPApp().recall(obj_id)
        obj.gui_params = params

    @rpcwrap
    def set_gui_created(self, obj_id, value):
        obj = MFPApp().recall(obj_id)
        obj.gui_created = value

    @rpcwrap
    def get_info(self, obj_id):
        obj = MFPApp().recall(obj_id)
        return dict(num_inlets=len(obj.inlets),
                    num_outlets=len(obj.outlets),
                    dsp_inlets=obj.dsp_inlets,
                    dsp_outlets=obj.dsp_outlets)

    @rpcwrap
    def log_write(self, msg):
        MFPApp().gui_cmd.log_write(msg)

    @rpcwrap
    def console_eval(self, cmd):
        return MFPApp().console.runsource(cmd)

    @rpcwrap
    def add_scope(self, scope_name):
        MFPApp().patches["default"].add_scope(scope_name)

    @rpcwrap
    def rename_scope(self, old_name, new_name):
        patch = MFPApp().patches['default']
        scope = patch.scopes.get(old_name)
        if scope:
            scope.name = new_name
        # FIXME merge scopes if changing to a used name?
        # FIXME signal send/receive objects to flush and re-resolve

    @rpcwrap
    def rename_obj(self, obj_id, new_name):
        obj = MFPApp().recall(obj_id)
        patch = obj.patch
        scope = obj.scope
        obj.assign(patch, scope, new_name)

    @rpcwrap
    def set_scope(self, obj_id, scope_name):
        obj = MFPApp().recall(obj_id)
        if obj is None:
            log.debug("Cannot find object for %d to set scope to %s" % (obj_id, scope_name))
            return

        scope = obj.patch.scopes.get(scope_name)

        log.debug("Reassigning scope for obj", obj_id, "to", scope_name)
        obj.assign(obj.patch, scope, obj.name)

    @rpcwrap
    def quit(self):
        MFPApp().finish()


class MFPApp (Singleton):
    no_gui = False
    no_dsp = False

    def __init__(self):
        self.dsp_process = None
        self.dsp_command = None 

        self.gui_process = None
        self.gui_cmd = None

        # threads in this process
        self.midi_mgr = None
        self.osc_mgr = None
        self.console = None

        # processor class registry
        self.registry = {}

        # objects we have given IDs to
        self.objects = {}
        self.next_obj_id = 0

        # temporary name cache
        self.objects_byname = {}

        self.app_scope = LexicalScope()
        self.patches = {}

    def setup(self):
        from mfp.dsp_slave import dsp_init, DSPObject, DSPCommand
        from mfp.gui_slave import gui_init, GUICommand

        RPCWrapper.node_id = "MFP Master"
        MFPCommand.local = True

        # dsp and gui processes
        if not MFPApp.no_dsp:
            num_inputs = 2
            num_outputs = 2
            self.dsp_process = RPCServer("mfp_dsp", dsp_init, num_inputs, num_outputs)
            self.dsp_process.start()
            self.dsp_process.serve(DSPObject)
            self.dsp_process.serve(DSPCommand)
            self.dsp_command = DSPCommand()
            self.samplerate, self.blocksize = self.dsp_command.get_dsp_params()

        if not MFPApp.no_gui:
            self.gui_process = RPCServer("mfp_gui", gui_init)
            self.gui_process.start()
            self.gui_process.serve(GUICommand)
            self.gui_cmd = GUICommand()
            while not self.gui_cmd.ready():
                time.sleep(0.2)
            log.debug("GUI is ready, switching logging to GUI")
            log.log_func = self.gui_cmd.log_write
            log.debug("Started logging to GUI")
            if self.dsp_command:
                self.dsp_command.log_to_gui()

            self.console = Interpreter(self.gui_cmd.console_write, dict(app=self))
            self.gui_cmd.hud_write("<b>Welcome to MFP</b>")

        # midi manager
        from . import midi
        self.midi_mgr = midi.MFPMidiManager(1, 1)
        self.midi_mgr.start()
        log.debug("MIDI started (ALSA Sequencer)")

        # OSC manager
        from . import osc
        self.osc_mgr = osc.MFPOscManager(5555)
        self.osc_mgr.start()
        log.debug("OSC server started (UDP/5555)")

    def remember(self, obj):
        oi = self.next_obj_id
        self.next_obj_id += 1
        self.objects[oi] = obj
        obj.obj_id = oi

        return oi

    def recall(self, obj_id):
        return self.objects.get(obj_id)

    def forget(self, obj):
        try:
            del self.objects[obj.obj_id]
        except KeyError:
            pass 

    def register(self, name, ctor):
        self.registry[name] = ctor

    def create(self, init_type, init_args, patch, scope, name):
        ctor = self.registry.get(init_type)
        if ctor is None:
            log.debug("No factory for '%s' registered, looking for file." % init_type)
            (typename, ctor) = Patch.register_file(init_type + ".mfp")
            if ctor is None:
                return None

        # factory found, use it
        try:
            obj = ctor(init_type, init_args, patch, scope, name)
            if obj and obj.obj_id:
                obj.mark_ready()
            return obj
        except Exception, e:
            log.debug("Caught exception while trying to create %s (%s)"
                      % (init_type, init_args))
            log.debug(e)
            import traceback
            traceback.print_exc()
            self.cleanup()
            return None

    def cleanup(self):
        garbage = [] 
        for oid, obj in self.objects.items():
            if obj.status == Processor.CTOR:
                garbage.append(obj)

        for obj in garbage: 
            if obj.patch is not None:
                obj.patch.remove(obj)
                obj.patch = None 

            obj.delete()

    def resolve(self, name, queryobj=None):
        '''
        Attempt to identify an object matching name

        If name has '.'-separated parts, use simple logic to treat
        parts as a path.  First match to the first element roots the
        search path; i.e. "foo.bar.baz" will match the first foo in
        the search path, and the first bar under that foo
        '''

        def find_part(part, base):
            if isinstance(base, (Patch, LexicalScope)):
                return base.resolve(part)
            return None

        parts = name.split('.')
        obj = None
        root = None

        # first find the base
        if queryobj and queryobj.patch:
            root = queryobj.patch.resolve(parts[0], queryobj.scope)
        if not root:
            for pname, pobj in self.patches.items():
                root = pobj.resolve(parts[0])

                if root:
                    break

        # now descend the path
        if root:
            obj = root
            for p in parts[1:]:
                obj = find_part(p, obj)

        return obj

    def finish(self):
        log.log_func = None
        if self.console:
            self.console.write_cb = None

        if self.dsp_process:
            log.debug("MFPApp.finish: reaping DSP slave...")
            self.dsp_process.finish()

        if self.gui_process:
            log.debug("MFPApp.finish: reaping GUI slave...")
            self.gui_process.finish()

        from quittable_thread import QuittableThread
        log.debug("MFPApp.finish: reaping threads...")
        QuittableThread.finish_all()

        log.debug("MFPApp.finish: all children reaped, good-bye!")


def main():
    import math
    import os
    import sys
    import re
    from mfp import builtins

    log.debug("Main thread started, pid =", os.getpid())
    # log.log_file = open("mfp.log", "w+")

    app = MFPApp()
    app.setup()

    # default names known to the evaluator
    Evaluator.bind_global("math", math)
    Evaluator.bind_global("os", os)
    Evaluator.bind_global("sys", sys)
    Evaluator.bind_global("re", re)

    from mfp.bang import Bang, Uninit
    from mfp.method import MethodCall
    Evaluator.bind_global("Bang", Bang)
    Evaluator.bind_global("Uninit", Uninit)
    Evaluator.bind_global("MethodCall", MethodCall)

    from mfp.midi import NoteOn, NoteOff
    Evaluator.bind_global("NoteOn", NoteOn)
    Evaluator.bind_global("NoteOff", NoteOff)

    Evaluator.bind_global("builtins", builtins)
    Evaluator.bind_global("app", app)

    builtins.register()

    if len(sys.argv) > 2:
        initargs = sys.argv[2]
    else:
        initargs = None

    if len(sys.argv) > 1:
        log.debug("main: loading", sys.argv[1])

        name, factory = Patch.register_file(sys.argv[1])
        patch = factory(name, initargs, None, app.app_scope, name)
    else:
        patch = Patch('default', '', None, app.app_scope, 'default')

    app.patches["default"] = patch
    patch.mark_ready()
    patch.create_gui()
