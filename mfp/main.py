#! /usr/bin/env python
'''
main.py: main routine for mfp

Copyright (c) 2010-2012 Bill Gribble <grib@billgribble.com>
'''

import time
import math 
import re 
import sys, os 
import argparse
import ConfigParser
import simplejson as json

from .bang import Bang
from .patch import Patch
from .scope import LexicalScope
from .singleton import Singleton
from .interpreter import Interpreter
from .evaluator import Evaluator
from .processor import Processor
from .method import MethodCall
from .quittable_thread import QuittableThread 
from .rpc_wrapper import RPCWrapper, rpcwrap
from .rpc_worker import RPCServer
from .patch_json import ExtendedEncoder, extended_decoder_hook

from pluginfo import PlugInfo 

from . import log
from . import builtins 
from . import utils

class StartupError(Exception):
    pass 

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
    def send_methodcall(self, obj_id, port, method, *args, **kwargs): 
        obj = MFPApp().recall(obj_id)
        m = MethodCall(method, *args, **kwargs)
        obj.send(m, port)

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
    def set_do_onload(self, obj_id, value):
        obj = MFPApp().recall(obj_id)
        obj.do_onload = value 

    @rpcwrap
    def get_info(self, obj_id):
        obj = MFPApp().recall(obj_id)
        return dict(num_inlets=len(obj.inlets),
                    num_outlets=len(obj.outlets),
                    dsp_inlets=obj.dsp_inlets,
                    dsp_outlets=obj.dsp_outlets)
    
    @rpcwrap
    def get_tooltip(self, obj_id, direction=None, portno=None):
        obj = MFPApp().recall(obj_id)
        return obj.tooltip(direction, portno)

    @rpcwrap
    def log_write(self, msg):
        MFPApp().gui_command.log_write(msg)

    @rpcwrap
    def console_eval(self, cmd):
        return MFPApp().console.runsource(cmd)

    @rpcwrap
    def add_scope(self, patch_id, scope_name):
        patch = MFPApp().recall(patch_id)
        patch.add_scope(scope_name)

    @rpcwrap
    def rename_scope(self, patch_id, old_name, new_name):
        patch = MFPApp().recall(patch_id)
        scope = patch.scopes.get(old_name)
        if scope:
            scope.name = new_name
        # FIXME merge scopes if changing to a used name?
        # FIXME signal send/receive objects to flush and re-resolve

    @rpcwrap
    def rename_obj(self, obj_id, new_name):
        obj = MFPApp().recall(obj_id)
        obj.rename(new_name)

    @rpcwrap
    def set_scope(self, obj_id, scope_name):
        obj = MFPApp().recall(obj_id)
        if obj is None:
            log.debug("Cannot find object for %s to set scope to %s" % (obj_id, scope_name))
            return

        scope = obj.patch.scopes.get(scope_name)

        log.debug("Reassigning scope for obj", obj_id, "to", scope_name)
        obj.assign(obj.patch, scope, obj.name)

    @rpcwrap
    def open_file(self, file_name):
        MFPApp().open_file(file_name)

    @rpcwrap
    def save_file(self, patch_name, file_name):
        patch = MFPApp().patches.get(patch_name)
        if patch:
            patch.save_file(file_name)

    @rpcwrap
    def clipboard_copy(self, pointer_pos, objlist):
        return MFPApp().clipboard_copy(pointer_pos, objlist)

    @rpcwrap
    def clipboard_paste(self, json_txt, patch_id, scope_name, mode):
        patch = MFPApp().recall(patch_id)
        scope = patch.scopes.get(scope_name)
        return MFPApp().clipboard_paste(json_txt, patch, scope, mode)

    @rpcwrap
    def quit(self):
        MFPApp().finish()


class MFPApp (Singleton):
    def __init__(self):
        # configuration items -- should be populated before calling setup() 
        self.no_gui = False
        self.no_dsp = False
        self.osc_port = None 
        self.searchpath = None 
        self.extpath = None 
        self.dsp_inputs = 2
        self.dsp_outputs = 2
        self.samplerate = 44100
        self.blocksize = 256 
        self.max_blocksize = 2048 
        self.in_latency = 0
        self.out_latency = 0

        # multiprocessing targets and RPC links
        self.dsp_process = None
        self.dsp_command = None 

        self.gui_process = None
        self.gui_command = None

        # threads in this process
        self.midi_mgr = None
        self.osc_mgr = None
        self.console = None

        # True if NSM_URL set on launch 
        self.session_managed = None 
        self.session_dir = None 
        self.session_id = None 

        # app callbacks 
        self.callbacks = {}
        self.callbacks_last_id = 0

        # processor class registry
        self.registry = {}

        # objects we have given IDs to
        self.objects = {}
        self.next_obj_id = 0

        # plugin info database
        self.pluginfo = PlugInfo()
        self.app_scope = LexicalScope()
        self.patches = {}

    def setup(self):
        from mfp.dsp_slave import dsp_init, DSPObject, DSPCommand
        from mfp.gui_slave import gui_init, GUICommand

        RPCWrapper.node_id = "MFP Master"
        MFPCommand.local = True

        log.debug("Main thread started, pid = %s" % os.getpid())

        # dsp and gui processes
        if not self.no_dsp:
            self.dsp_process = RPCServer("mfp_dsp", dsp_init, "mfp",
                                         self.max_blocksize, self.dsp_inputs, self.dsp_outputs)
            self.dsp_process.start()
            self.dsp_process.serve(DSPObject)
            self.dsp_process.serve(DSPCommand)
            self.dsp_command = DSPCommand()
            params = self.dsp_command.get_dsp_params() 
            if params is not None: 
                self.samplerate, self.blocksize = params

            params = self.dsp_command.get_latency() 
            if params is not None: 
                self.in_latency, self.out_latency = params

            if not self.dsp_process.alive():
                raise StartupError("DSP process died during startup")

        if not self.no_gui:
            self.gui_process = RPCServer("mfp_gui", gui_init)
            self.gui_process.start()
            self.gui_process.serve(GUICommand)
            self.gui_command = GUICommand()

            while self.gui_process.alive() and not self.gui_command.ready():
                time.sleep(0.2)

            if not self.gui_process.alive():
                raise StartupError("GUI process died during setup")

            log.debug("GUI is ready, switching logging to GUI")
            log.log_func = self.gui_command.log_write

            log.debug("Started logging to GUI")
            if self.dsp_command:
                self.dsp_command.log_to_gui()

            self.console = Interpreter(self.gui_command.console_write, dict(app=self))
            self.gui_command.hud_write("<b>Welcome to MFP %s</b>" % version())

        # midi manager
        from . import midi
        self.midi_mgr = midi.MFPMidiManager(1, 1)
        self.midi_mgr.start()
        log.debug("MIDI started (ALSA Sequencer)")

        # OSC manager
        from . import osc
        self.osc_mgr = osc.MFPOscManager(self.osc_port)
        self.osc_mgr.start()
        log.debug("OSC server started (UDP/%s)" % self.osc_port)

        # crawl plugins 
        log.debug("Collecting information about installed plugins...")
        self.pluginfo.samplerate = self.samplerate 
        self.pluginfo.index_ladspa()
        log.debug("Found %d LADSPA plugins in %d files" % (len(self.pluginfo.pluginfo), 
                                                           len(self.pluginfo.libinfo)))

    def remember(self, obj):
        oi = self.next_obj_id
        self.next_obj_id += 1
        self.objects[oi] = obj
        obj.obj_id = oi

        return oi

    def recall(self, obj_id):
        return self.objects.get(obj_id, self)

    def forget(self, obj):
        try:
            del self.objects[obj.obj_id]
        except KeyError:
            pass 

    def register(self, name, ctor):
        self.registry[name] = ctor

    def open_file(self, file_name):
        if file_name is not None:
            log.debug("Opening patch file", file_name)
            name, factory = Patch.register_file(file_name)
            patch = factory(name, "", None, self.app_scope, name)
        else:
            patch = Patch('default', '', None, self.app_scope, None)
            patch.gui_params['layers'] = [ ('Layer 0', '__patch__') ]

        self.patches[patch.name] = patch 
        patch.create_gui()
        patch.mark_ready()

    def load_extension(self, libname):
        fullpath = utils.find_file_in_path(libname, self.extpath)
        self.dsp_command.ext_load(fullpath)

    def create(self, init_type, init_args, patch, scope, name):
        # first try: is a factory registered? 
        ctor = self.registry.get(init_type)

        # second try: is there a .mfp patch file in the search path? 
        if ctor is None:
            log.debug("No factory for '%s' registered, looking for file." % init_type)
            filename = init_type + ".mfp"
            filepath = utils.find_file_in_path(filename, self.searchpath)

            if filepath: 
                log.debug("Found file", filepath)
                (typename, ctor) = Patch.register_file(filepath)
            else:
                log.debug("No file '%s' in search path %s" % (filename, MFPApp().searchpath))

        # third try: can we autowrap a python function? 
        if ctor is None: 
            try: 
                thunk = patch.parse_obj(init_type)
                if callable(thunk): 
                   ctor = builtins.pyfunc.PyAutoWrap
            except Exception, e: 
                log.debug("Cannot autowrap %s as a Python callable" % init_type)
                print e

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

        # first find the base. 
        # 1. Look in the queryobj's patch 
        if queryobj and queryobj.patch:
            root = queryobj.patch.resolve(parts[0], queryobj.scope)

        # 2. Try the global scope 
        if not root:
            root = self.app_scope.resolve(parts[0]) 

        # 3. Check the patch-scope of all the loaded patches. 
        # (this is pretty suspect)
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

        log.debug("MFPApp.finish: reaping threads...")
        QuittableThread.finish_all()

        log.debug("MFPApp.finish: all children reaped, good-bye!")


    def send(self, msg, port): 
        msgid, msgval = msg 
        if msgid == 1: # latency changed  
            self.emit_signal("latency") 

    #####################
    # callbacks
    #####################

    def add_callback(self, signal_name, callback): 
        cbid = self.callbacks_last_id
        self.callbacks_last_id += 1

        oldlist = self.callbacks.setdefault(signal_name, [])
        oldlist.append((cbid, callback))

        return cbid

    def remove_callback(self, cb_id):
        for signal, hlist in self.callbacks.items():
            for num, cbinfo in enumerate(hlist):
                if cbinfo[0] == cb_id:
                    hlist[num:num+1] = [] 
                    return True 
        return False

    def emit_signal(self, signal_name, *args):
        for cbinfo in self.callbacks.get(signal_name, []):
            cbinfo[1](*args)
  
    def session_management_setup(self): 
        from . import nsm 
        self.session_managed = nsm.init_nsm()

    def session_init(self, session_path, session_id):
        import os
        os.mkdir(session_path)
        self.session_dir = session_path 
        self.session_id = session_id 
        self.session_save()

        # reinitialize JACK 
        if self.dsp_command:
            self.dsp_command.reinit(self.session_id, self.max_blocksize, 
                                    self.dsp_inputs, self.dsp_outputs)

    def session_save(self):
        import os.path

        sessfile = open(os.path.join(self.session_dir, "session_data"), "w+")
        if sessfile is None: 
            return None 
        
        cp = ConfigParser.SafeConfigParser(allow_no_value=True)
        cp.add_section("mfp")

        for attr in ("no_gui", "no_dsp", "dsp_inputs", "dsp_outputs", 
                     "osc_port", "searchpath", "extpath", "max_blocksize"):
            val = getattr(self, attr)
            if isinstance(val, str):
                val = '"%s"' % val 
            else: 
                val = str(val)
            cp.set("mfp", attr, val)

        patches = [] 
        for obj_id, patch in self.patches.items():
            patch.save_file(os.path.join(self.session_dir, patch.name + '.mfp'))
            patches.append(patch.name + '.mfp')

        cp.set("mfp", "patches", str(patches))
        cp.write(sessfile)
        sessfile.close()

    def session_load(self, session_path, session_id):
        self.session_dir = session_path 
        self.session_id = session_id 
        cp = ConfigParser.SafeConfigParser(allow_no_value=True)
        
        print "MFPApp.session_load: loading", session_path, session_id 

        print "about to read session file in", self.session_dir
        cp.read(os.path.join(self.session_dir, "session_data"))

        for attr in ("no_gui", "no_dsp", "dsp_inputs", "dsp_outputs", 
                     "osc_port", "searchpath", "extpath", "max_blocksize"):
            val = cp.get("mfp", attr)
            if not val: 
                val = "''"
            setattr(self, attr, eval(val))


        # reinitialize JACK 
        if self.dsp_command:
            self.dsp_command.reinit(self.session_id, self.max_blocksize, 
                                    self.dsp_inputs, self.dsp_outputs)

        patches = eval(cp.get("mfp", "patches")) 

        # if we made it this far, clean up the existing session and go
        for obj_id, patch in self.patches.items():
            patch.delete_gui()
            patch.delete()
        self.patches = {} 

        self.searchpath = utils.prepend_path(session_path, self.searchpath)
        self.extpath = utils.prepend_path(session_path, self.extpath)

        for p in patches: 
            self.open_file(p)
       
    def clipboard_copy(self, pointer_pos, obj_ids):
        toplevel = {} 
        objects = {} 

        free_conn_in = [] 
        free_conn_out = [] 

        # save connections into and out of the set of objects 
        for o in obj_ids:
            srcobj = self.recall(o)

            objects[srcobj.obj_id] = srcobj.save()

            for port_num, port_conn in enumerate(srcobj.connections_in):
                for tobj, tport in port_conn:
                    if tobj.obj_id not in obj_ids: 
                        free_conn_in.append((tobj.obj_id, tport, o, port_num))

            for port_num, port_conn in enumerate(srcobj.connections_out):
                for tobj, tport in port_conn:
                    if tobj.obj_id not in obj_ids: 
                        free_conn_out.append((tobj.obj_id, tport, o, port_num))

        # return JSON 
        toplevel['free_conn_in'] = free_conn_in
        toplevel['free_conn_out'] = free_conn_out 
        toplevel['pointer'] = pointer_pos
        toplevel['objects'] = objects 
        toplevel['mfp_version'] = version()
        js = json.dumps(toplevel, indent=4, cls=ExtendedEncoder)
        return js 

    def clipboard_paste(self, json_text, patch, scope, paste_mode):
        print "clipboard_paste: got json text"
        print json_text
        
        jdata = json.loads(json_text, object_hook=extended_decoder_hook)
        idmap = patch.json_unpack_objects(jdata, scope)
        patch.json_unpack_connections(jdata, idmap)
        return [ o.obj_id for o in idmap.values() ]

def version():
    import pkg_resources 
    vers = pkg_resources.require("mfp")[0].version
    return vers

def add_evaluator_defaults(): 
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

    from mfp.midi import NoteOn, NoteOff, NotePress, MidiCC, MidiPgmChange
    Evaluator.bind_global("NoteOn", NoteOn)
    Evaluator.bind_global("NoteOff", NoteOff)
    Evaluator.bind_global("NotePress", NotePress)
    Evaluator.bind_global("MidiCC", MidiCC)
    Evaluator.bind_global("MidiPgmChange", MidiPgmChange)

    Evaluator.bind_global("builtins", builtins)
    Evaluator.bind_global("app", MFPApp())

mfp_banner = "MFP - Music For Programmers, version %s"

mfp_footer = """
To report bugs or download source: 
    
    http://github.com/bgribble.mfp 

Copyright (c) 2009-2013 Bill Gribble <grib@billgribble.com> 

MFP is free software, and you are welcome to redistribute it 
under certain conditions.  See the file COPYING for details.
"""

def exit_sighandler(signum, frame):
    log.log_force_console = True 
    log.debug("Received terminating signal %s, exiting" % signum)
    sys.exit(-signum)

def main():
    description = mfp_banner % version() 

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=description, epilog=mfp_footer)
    
    parser.add_argument("patchfile", nargs='*', 
                        help="Patch files to load")
    parser.add_argument("-f", "--init-file", action="append",
                        default=[utils.homepath(".mfp/mfprc.py")],
                        help="Python source file to exec at launch")
    parser.add_argument("-p", "--patch-path", action="append",
                        default=[os.getcwd()],
                        help="Search path for patch files")
    parser.add_argument("-l", "--init-lib", action="append", default=[],
                        help="Extension library (*.so) to load at launch")
    parser.add_argument("-L", "--lib-path", action="append", default=[],
                        help="Search path for extension libraries")
    parser.add_argument("-i", "--inputs", default=2, type=int,
                        help="Number of JACK audio input ports")
    parser.add_argument("-o", "--outputs", default=2, type=int,
                        help="Number of JACK audio output ports")
    parser.add_argument("-u", "--osc-udp-port", default=5555, type=int, 
                        help="UDP port to listen for OSC (default: 5555)")
    parser.add_argument("--max-bufsize", default=2048,
                        help="Maximum JACK buffer size to support (default: 2048 frames)")
    parser.add_argument("--no-gui", action="store_true", 
                        help="Do not launch the GUI engine")
    parser.add_argument("--no-dsp", action="store_true", 
                        help="Do not launch the DSP engine")
    parser.add_argument("--help-builtins", action="store_true", 
                        help="Display help on builtin objects and exit") 

    args = vars(parser.parse_args())

    # create the app object 
    app = MFPApp()
   
    # configure some things from command line
    app.no_gui = args.get("no_gui") or args.get("help_builtins")
    app.no_dsp = args.get("no_dsp")
    app.dsp_inputs = args.get("inputs")
    app.dsp_outputs = args.get("outputs")
    app.osc_port = args.get("osc_udp_port")
    app.searchpath = ':'.join(args.get("patch_path"))
    app.extpath = ':'.join(args.get("lib_path"))
    app.max_blocksize = args.get("max_bufsize") 

    # launch processes and threads 
    import signal
    signal.signal(signal.SIGTERM, exit_sighandler)

    try: 
        app.setup()
    except (StartupError, KeyboardInterrupt, SystemExit):
        log.debug("Setup did not complete properly, exiting")
        app.finish()
        return 

    # ok, now start configuring the running system  
    add_evaluator_defaults() 
    builtins.register()

    for libname in args.get("init_lib"):
        app.load_extension(libname)


    evaluator = Evaluator()

    pyfiles = args.get("init_file", [])
    for f in pyfiles: 
        fullpath = utils.find_file_in_path(f, app.searchpath)
        log.debug("initfile: Looking for", f)
        if not fullpath: 
            log.debug("initfile: Cannot find file %s, skipping" % f) 
            continue

        try: 
            os.stat(fullpath)
        except OSError: 
            log.debug("initfile: Error accessing file", fullpath) 
            continue
        try: 
            evaluator.exec_file(fullpath)
        except Exception, e: 
            log.debug("initfile: Exception while loading initfile", f) 
            log.debug(e)

    if args.get("help_builtins"):
        app.open_file(None)
        for name, factory in sorted(app.registry.items()): 
            if hasattr(factory, 'doc_tooltip_obj'):
                print "%-12s : %s" % ("[%s]" % name, factory.doc_tooltip_obj) 
            else: 
                try: 
                    o = factory(name, None, app.patches['patch'], None, "")
                    print "%-12s : %s" % ("[%s]" % name, o.doc_tooltip_obj) 
                except Exception, e:
                    import traceback
                    print "(caught exception trying to create %s)" % name, e
                    traceback.print_exc()
                    print "%-12s : No documentation found" % ("[%s]" % name,)
        app.finish()
    else: 
        # create initial patch
        patchfiles = args.get("patchfile")
        if len(patchfiles): 
            print "Opening patch files:", patchfiles

            for p in patchfiles: 
                app.open_file(p)
        else: 
            app.open_file(None)

        # allow session management 
        app.session_management_setup()

        try: 
            QuittableThread.wait_for_all()
        except (KeyboardInterrupt, SystemExit):
            log.log_force_console = True 
            log.debug("Quit request received, exiting")
            app.finish()

