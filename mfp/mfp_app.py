"""
mfp_app.py

Declare the main MFPApp object that holds app state in the GUI process
"""

import asyncio
import inspect
import os
import os.path
import configparser
import simplejson as json

from .patch import Patch
from .patch_json import ExtendedEncoder, extended_decoder_hook
from .scope import LexicalScope
from .singleton import Singleton
from .interpreter import Interpreter
from .processor import Processor
from .method import MethodCall
from .utils import QuittableThread, AsyncExecMonitor, AsyncTaskManager, SignalMixin
from .bang import Unbound

from pluginfo import PlugInfo

from . import log
from . import builtins
from . import utils


class StartupError(Exception):
    pass


class MFPApp (Singleton, SignalMixin):
    def __init__(self):
        super().__init__()

        # configuration items -- should be populated before calling setup()
        self.no_gui = False
        self.no_dsp = False
        self.no_restart = False
        self.no_onload = False
        self.gui_backend = None
        self.debug = False
        self.debug_remote = False
        self.osc_port = None
        self.searchpath = None
        self.extpath = None
        self.lv2_savepath = "lv2"
        self.dsp_inputs = 2
        self.dsp_outputs = 2
        self.midi_inputs = 1
        self.midi_outputs = 1
        self.samplerate = 44100
        self.blocksize = 256
        self.max_blocksize = 2048
        self.socket_path = "/tmp/mfp_rpcsock"
        self.batch_mode = False
        self.batch_obj = None
        self.batch_args = None
        self.batch_eval = False
        self.batch_input_file = None

        # RPC host
        self.rpc_listener = None
        self.rpc_host = None

        # multiprocessing targets and RPC links
        self.dsp_process = None

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

        self.leftover_threads = []

        # processor class registry
        self.registry = {}

        # objects we have given IDs to
        self.objects = {}
        self.next_obj_id = 0

        # plugin info database
        self.pluginfo = PlugInfo()
        self.app_scope = LexicalScope("__app__")
        self.patches = {}

        # helper to run async task
        self.async_task = AsyncTaskManager()

    async def setup(self):
        from .mfp_command import MFPCommand
        from .gui_command import GUICommand
        from .mfp_main import version
        from carp.channel import UnixSocketChannel
        from carp.host import Host

        log.info(f"Starting MFP v{version()} pid={os.getpid()}")

        # RPC service setup
        self.rpc_channel = UnixSocketChannel(socket_path=self.socket_path)
        self.rpc_host = Host(
            label="MFP Master",
        )
        self.rpc_host.on("disconnect", self.on_host_disconnect)
        self.rpc_host.on("accept", self.on_host_connect)
        self.rpc_host.on("exports", self.on_host_exports)
        self.rpc_host.on("debug", lambda event, msg: log.debug(msg))

        def _exception(exc, tbinfo, traceback=""):
            log.error(f"[rpc] Exception: {tbinfo}")
            for ll in traceback.split('\n'):
                log.error(ll)

        self.rpc_host.on("exception", _exception)

        await self.rpc_host.start(self.rpc_channel)

        # classes served by this RPC host:
        await self.rpc_host.export(MFPCommand)

        # dsp and gui processes
        await self.start_dsp()

        if not self.no_gui:
            logstart = log.log_time_base.strftime("%Y-%m-%dT%H:%M:%S.%f")
            guicmd = [
                "mfpgui",
                "-s", self.socket_path,
                "-l", logstart,
                '--backend', self.gui_backend,
                "--searchpath", self.searchpath
            ]
            if self.debug:
                guicmd.append('--debug')

            self.gui_process = AsyncExecMonitor(
                *guicmd,
                log_module="gui",
                log_raw=self.debug_remote
            )
            await self.gui_process.start()

            GUICommandFactory = await self.rpc_host.require(GUICommand)

            self.gui_command = await GUICommandFactory()

            log.debug("Switching logging to GUI. Start with -v to always log to console.")
            log.log_func = self.gui_command.log_write

            self.console = Interpreter(dict(app=self))

            await self.gui_command.hud_write(f"<b>Welcome to MFP {version()}</b>")

            # midi manager
            self.start_midi()

            # OSC manager
            from . import osc
            self.osc_mgr = osc.MFPOscManager(self.osc_port)
            self.osc_mgr.start()
            self.osc_port = self.osc_mgr.port
            log.debug("OSC server started (UDP/%s)" % self.osc_port)

            # crawl plugins
            log.debug("Collecting information about installed plugins...")
            self.async_task(self.index_plugins())


    async def index_plugins(self):
        self.pluginfo.samplerate = self.samplerate
        await asyncio.to_thread(self.pluginfo.index_ladspa)
        log.debug(
            "Found %d LADSPA plugins in %d files" % (
                len(self.pluginfo.pluginfo), len(self.pluginfo.libinfo))
        )

    async def exec_batch(self):
        # configure logging
        log.log_quiet = True
        log.log_raw = True
        log.log_debug = False
        log.log_force_console = False

        await self.open_file(None)
        p = self.patches.get('default')

        # create a patch that iterates over the lines of stdin
        # and feeds each one into the patch on the command line
        reader = await self.create(
            "file",
            self.batch_input_file or "sys.stdin",
            p, p.default_scope, "reader")
        trig = await self.create("trigger", "2", p, p.default_scope, "trig")
        eoftest = await self.create("case", "EOF", p, p.default_scope, "eoftest")
        stripper = await self.create("strip", None, p, p.default_scope, "strip")
        evaluator = None

        if self.batch_eval:
            evaluator = await self.create("eval", None, p, p.default_scope, "evaluator")

        batch = await self.create(
            self.batch_obj,
            self.batch_args,
            p,
            p.default_scope,
            "batch"
        )
        printer = await self.create("print", None, p, p.default_scope, "printer")
        msg = await self.create("message", "@readline", p, p.default_scope, "nextline")

        await reader.connect(0, trig, 0)
        await trig.connect(0, eoftest, 0)
        await trig.connect(1, stripper, 0)
        await eoftest.connect(1, msg, 0)

        if self.batch_eval:
            await stripper.connect(0, evaluator, 0)
            await evaluator.connect(0, batch, 0)
        else:
            await stripper.connect(0, batch, 0)
        await batch.connect(0, printer, 0)
        await msg.connect(0, reader, 0)

        # start the reader
        await reader.send(MethodCall("readline"))

    def start_midi(self):
        from . import midi
        if self.midi_mgr:
            self.midi_mgr.finish()
        self.midi_mgr = midi.MFPMidiManager(self.midi_inputs, self.midi_outputs)
        self.async_task(self.midi_mgr.run())
        log.debug("MIDI started (ALSA Sequencer)")

    async def start_dsp(self):
        from .dsp_object import DSPObject, DSPContext
        if self.dsp_process is not None:
            log.debug("Terminating old DSP process...")
            await self.dsp_process.cancel()
            self.dsp_process = None

        dspcommand = [
            #"valgrind", "--leak-check=full", "--track-origins=yes",
            "mfpdsp", self.socket_path, self.max_blocksize,
            self.dsp_inputs, self.dsp_outputs,
        ]
        if not self.no_dsp:
            self.dsp_process = AsyncExecMonitor(
                *dspcommand, log_module="dsp", log_raw=self.debug_remote
            )
            await self.dsp_process.start()
            await self.rpc_host.require(DSPObject)
            Patch.default_context = DSPContext.lookup(
                self.rpc_host.services_remote["DSPObject"][0], 0
            )
            log.debug(f"DSP backend started, context={Patch.default_context}")

    def remember(self, obj):
        oi = self.next_obj_id
        self.next_obj_id += 1
        self.objects[oi] = obj
        obj.obj_id = oi

        return oi

    def recall(self, obj_id):
        return self.objects.get(obj_id, None)

    def forget(self, obj):
        try:
            del self.objects[obj.obj_id]
        except KeyError:
            pass

    def register(self, name, ctor):
        self.registry[name] = ctor

    async def on_host_exports(self, event, peer_id, exports, metadata):
        from .dsp_object import DSPContext
        if "DSPObject" in exports:
            context = DSPContext.lookup(peer_id, 0)
            context.input_latency, context.output_latency = metadata

    async def on_host_connect(self, event, peer_id):
        log.debug(f"Got connect callback for {peer_id} {event}")

    async def on_host_disconnect(self, event, peer_id):
        # if we lost a DSP host, try to restart
        log.debug(f"Got disconnect callback for {peer_id}")

        dead_patches = [
            p for p in self.patches.values()
            if p.context is None or p.context.node_id == peer_id
        ]
        if (
            Patch.default_context and (peer_id == Patch.default_context.node_id)
            and not self.no_restart
        ):
            log.warning("Relaunching default backend (old id=%s)" % peer_id)
            patch_json = []

            for p in dead_patches:
                patch_json.append(await p.json_serialize())
                await p.delete_gui()
                p.context = None
                await p.delete()

            if self.no_restart:
                return

            # delete and restart dsp backend
            await self.start_dsp()
            log.debug(f"relaunch: {len(patch_json)} patches to recreate")

            # recreate patches
            for jdata in patch_json:
                jobj = json.loads(jdata)
                name = jobj.get("gui_params", {}).get("name")
                patch = Patch(name, '', None, self.app_scope, name, Patch.default_context)
                self.patches[patch.name] = patch

                await patch.json_deserialize(jdata)
                patch.gui_params["dsp_context"] = patch.context.context_name
                if not MFPApp().no_onload:
                    await patch._run_onload(list(patch.objects.values()))
                await patch.create_gui()

        else:
            log.warning("Cleaning up RPC objects for remote (id=%s)" % peer_id)
            log.warning("DSP backend exited with no-restart flag, not restarting")
            for p in dead_patches:
                await p.delete()
            log.debug("Finished cleaning up patches")

    async def open_file(self, file_name, context=None, show_gui=True, **kwargs):
        from datetime import datetime

        starttime = datetime.now()
        patch = None
        factory = None
        name = 'default'

        if file_name is not None:
            loadpath = os.path.dirname(file_name)
            loadfile = os.path.basename(file_name)

            searchpath = self.searchpath + ((':' + loadpath) if loadpath else "")

            log.debug("Opening patch", loadfile)
            filepath = utils.find_file_in_path(loadfile, searchpath)

            if filepath:
                log.debug("Found file", filepath)
                (name, factory) = Patch.register_file(filepath)
            else:
                log.error("No file '%s' in search path %s" % (loadfile, searchpath))
                if "." in loadfile:
                    name = '.'.join(loadfile.split('.')[:-1])
                else:
                    name = loadfile
                factory = None

            if factory:
                patch = factory(name, "", None, self.app_scope, name, context)
                if inspect.isawaitable(patch):
                    patch = await patch

        if patch is None:
            patch = Patch(name, '', None, self.app_scope, name, context)
            patch.gui_params['layers'] = [('Layer 0', '__patch__')]

        if not self.no_dsp and not self.no_gui:
            context = patch.context
            await self.gui_command.dsp_info(dict(
                samplerate=self.samplerate,
                latency_in=context.input_latency,
                latency_out=context.output_latency,
                channels_in=self.dsp_inputs,
                channels_out=self.dsp_outputs
            ))

        self.patches[patch.name] = patch
        if show_gui:
            await patch.create_gui(**kwargs)
        patch.mark_ready()
        loadtime = datetime.now() - starttime
        log.debug("Patch loaded, elapsed time %s" % loadtime)
        if show_gui and patch.gui_created:
            await MFPApp().gui_command.select(patch.obj_id)
        return patch

    def load_extension(self, libname):
        fullpath = utils.find_file_in_path(libname, self.extpath)
        log.warning(f"mfp_app.load_extension: not implemented completely, path={fullpath}")

    async def create(self, init_type, init_args, patch, scope, name, params=None, setup=True):
        create_params = {}
        rval = None

        # first try: is a factory registered?
        ctor = self.registry.get(init_type)

        # try to compile code to get extra defs
        defs = {}
        if params and "code" in params:
            code = params.get("code")
            if code and code.get("lang") == "python":
                codestr = code.get("body")
                errinfo = patch.evaluator.exec_str(codestr, defs)
                if errinfo:
                    create_params["code"] = dict(body=codestr, lang="python", errorinfo=errinfo)
                    rval = create_params
                else:
                    create_params["code"] = dict(body=codestr, lang="python")

        # second try: is there a .mfp patch file in the search path?
        if ctor is None:
            filename = init_type + ".mfp"
            filepath = utils.find_file_in_path(filename, self.searchpath)

            if filepath:
                (_, ctor) = Patch.register_file(filepath)
                if not ctor:
                    log.debug(f"[create] Failed to load {init_type} from {filepath}")

        # third try: can we autowrap a python function?
        if ctor is None:
            try:
                thunk = patch.parse_obj(init_type, **defs)
                if callable(thunk):
                    ctor = builtins.pyfunc.PyAutoWrap
            except Exception as e:
                pass

        if ctor is None:
            log.error(f"[create] Could not find a build method for {init_type}")
            return rval

        # create intervening scope if needed
        if '.' in name:
            parts = name.split('.')
            if len(parts) > 2:
                log.error("Cannot deep-create name {}".format(name))
                return rval

            testobj = self.resolve(parts[0], patch, True)
            if testobj:
                if testobj is patch:
                    scope = None
                elif isinstance(testobj, Patch):
                    log.error(
                        "Cannot deep-create object {} in patch {}".format(name, testobj)
                    )
                    return rval
                elif not isinstance(scope, LexicalScope):
                    log.error(
                        "Cannot deep-create object {} in another object {}".format(name, testobj)
                    )
                    return rval
                else:
                    scope = testobj
            else:
                log.debug("Creating new scope {} in {}".format(parts[0], patch.name))
                newscope = patch.add_scope(parts[0])
                scope = newscope
            name = parts[1]

        # factory found, use it
        try:
            if defs != {}:
                obj = ctor(init_type, init_args, patch, scope, name, defs)
            else:
                obj = ctor(init_type, init_args, patch, scope, name)

            if inspect.isawaitable(obj):
                obj = await obj

            if obj and obj.obj_id:
                if setup:
                    await obj.setup()

                for attr, val in create_params.items():
                    obj.gui_params[attr] = val

                if obj.properties:
                    obj.conf(properties=obj.properties)

                obj.mark_ready()

            return obj
        except Exception as e:
            log.error("Caught exception while trying to create %s (%s)"
                      % (init_type, init_args))
            log.debug_traceback(e)
            await self.cleanup()
            return None

    async def cleanup(self):
        garbage = []
        for _, obj in self.objects.items():
            if obj.status == Processor.CTOR:
                garbage.append(obj)

        for obj in garbage:
            if obj.patch is not None:
                obj.patch.remove(obj)
                obj.patch = None

            await obj.delete()

    def resolve(self, name, queryobj=None, quiet=False):
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

        obj = Unbound
        root = Unbound
        if ':' in name:
            parts = name.split(':')
            if len(parts) > 2:
                return None

            queryobj = self.patches.get(parts[0])
            name = parts[1]
            if not queryobj:
                return None

        parts = name.split('.')

        # first find the base.

        # is the queryobj a patch? if so, resolve directly
        if queryobj and isinstance(queryobj, Patch):
            root = queryobj.resolve(parts[0])

        # Look in the queryobj's patch, if it's not a patch itself
        if (
            root is Unbound
            and queryobj and not isinstance(queryobj, Patch)
            and queryobj.patch
        ):
            root = queryobj.patch.resolve(parts[0], queryobj.scope)

            if root is Unbound:
                root = queryobj.patch.resolve(parts[0], queryobj.patch.default_scope)

        # now descend the path
        if root is not Unbound:
            obj = root
            for p in parts[1:]:
                obj = find_part(p, obj)

        if obj is not Unbound:
            return obj
        if not quiet:
            log.warning("resolve: can't resolve name '%s' in context %s"
                        % (name, queryobj))
        return None

    async def finish(self):
        log.log_func = None
        if self.console:
            self.console.write_cb = None

        Patch.default_context = None
        if self.dsp_process:
            pp = self.dsp_process
            self.dsp_process = None
            await pp.cancel()

        if self.gui_process:
            pp = self.gui_process
            self.gui_process = None
            await pp.cancel()

        if self.rpc_host:
            pp = self.rpc_host
            self.rpc_host = None
            await pp.stop()

        if QuittableThread._all_threads:
            QuittableThread.finish_all()

        if self.async_task:
            await self.async_task.finish()
            self.async_task = None

    async def finish_soon(self):
        import asyncio

        await asyncio.sleep(0.5)
        await self.finish()
        return True

    def send(self, msg, port):
        if isinstance(msg, MethodCall):
            msg.call(self)
        elif isinstance(msg, (list, tuple)):
            msgid, _ = msg
            # latency changed
            if msgid == 1:
                self.async_task(self.signal_emit("latency"))

    def session_management_setup(self):
        from . import nsm
        self.session_managed = nsm.init_nsm()

    def session_init(self, session_path, session_id):
        os.mkdir(session_path)
        self.session_dir = session_path
        self.session_id = session_id
        self.session_save()

    async def session_save(self):
        sessfile = open(os.path.join(self.session_dir, "session_data"), "w+")
        if sessfile is None:
            return None

        cp = configparser.SafeConfigParser(allow_no_value=True)
        cp.add_section("mfp")

        for attr in ("no_gui", "no_dsp", "dsp_inputs", "dsp_outputs",
                     "midi_inputs", "midi_outputs",
                     "osc_port", "searchpath", "extpath", "max_blocksize"):
            val = getattr(self, attr)
            if isinstance(val, str):
                val = '"%s"' % val
            else:
                val = str(val)
            cp.set("mfp", attr, val)

        patches = []
        for _, patch in self.patches.items():
            await patch.save_file(os.path.join(self.session_dir, patch.name + '.mfp'))
            patches.append(patch.name + '.mfp')

        cp.set("mfp", "patches", str(patches))
        cp.write(sessfile)
        sessfile.close()

    async def session_load(self, session_path, session_id):
        self.session_dir = session_path
        self.session_id = session_id
        cp = configparser.SafeConfigParser(allow_no_value=True)

        log.debug("Loading saved session", session_path, session_id)

        cp.read(os.path.join(self.session_dir, "session_data"))

        for attr in ("no_gui", "no_dsp", "dsp_inputs", "dsp_outputs",
                     "midi_inputs", "midi_outputs",
                     "osc_port", "searchpath", "extpath", "max_blocksize"):
            try:
                val = cp.get("mfp", attr)
                setattr(self, attr, eval(val))
            except KeyError:
                pass

        patches = eval(cp.get("mfp", "patches"))

        # if we made it this far, clean up the existing session and go
        for _, patch in list(self.patches.items()):
            await patch.delete_gui()
            await patch.delete()
        self.patches = {}

        self.searchpath = utils.prepend_path(session_path, self.searchpath)
        self.extpath = utils.prepend_path(session_path, self.extpath)

        self.no_restart = True
        await self.start_dsp()
        self.start_midi()
        for p in patches:
            await self.open_file(p)

    def clipboard_copy(self, pointer_pos, obj_ids):
        from .mfp_main import version
        toplevel = {}
        objects = {}
        scopes = {'__patch__': {}}

        free_conn_in = []
        free_conn_out = []

        # save connections into and out of the set of objects
        for o in obj_ids:
            srcobj = self.recall(o)

            objects[srcobj.obj_id] = srcobj.save()
            objscope = scopes.setdefault(srcobj.scope.name, {})
            objscope[srcobj.name] = srcobj.obj_id

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
        toplevel['scopes'] = scopes

        js = json.dumps(toplevel, indent=4, cls=ExtendedEncoder)
        return js

    async def clipboard_paste(self, json_text, patch, scope, paste_mode):
        jdata = json.loads(json_text, object_hook=extended_decoder_hook)
        idmap = await patch.json_unpack_objects(jdata, scope)
        await patch.json_unpack_connections(jdata, idmap)
        return [o.obj_id for o in idmap.values()]

    def toggle_pause(self):
        if Processor.paused:
            Processor.paused = False
        else:
            Processor.paused = True
        return Processor.paused
