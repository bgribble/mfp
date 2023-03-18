#! /usr/bin/env python
'''
processor.py: Parent class of all processors

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
import threading
from .dsp_object import DSPObject
from .method import MethodCall
from .evaluator import LazyExpr
from .bang import Uninit, Bang
from .scope import LexicalScope
from .utils import isiterable, task
from . import log


class AsyncOutput (object):
    def __init__(self, value, outlet):
        self.outlet_num = outlet
        self.value = value


class MultiOutput (object):
    def __init__(self):
        self.values = []


class Processor:
    PORT_IN = 0
    PORT_OUT = 1

    CTOR = 0
    READY = 1
    ERROR = 2
    DELETED = 3

    display_type = 'processor'
    save_to_patch = True
    hot_inlets = [0]
    do_onload = True
    clear_outlets = True

    paused = False

    doc_tooltip_obj = "No documentation found"
    doc_tooltip_inlet = []
    doc_tooltip_outlet = []

    def __init__(self, inlets, outlets, init_type, init_args, patch, scope, name):
        from .mfp_app import MFPApp

        self.init_type = init_type
        self.init_args = init_args
        self.obj_id = MFPApp().remember(self)

        self.inlets = [Uninit] * inlets
        self.outlets = [Uninit] * outlets
        self.outlet_order = list(range(outlets))

        self.status = Processor.CTOR
        self.tags = {}          # tags are labels shown in notify bubble
        self.properties = {}
        self.name = None
        self.patch = None
        self.scope = None

        # stats for inspector
        self.count_in = 0
        self.count_out = 0
        self.count_trigger = 0
        self.count_errors = 0

        # MIDI event listener
        self.midi_mode = None
        self.midi_filters = None
        self.midi_cbid = None
        self.midi_learn_cbid = None
        self.error_info = {}

        # OSC handling
        self.osc_pathbase = None
        self.osc_methods = []

        self.trigger_lock = threading.Lock()

        self.gui_created = False

        # gui_params are passed back and forth to the UI process
        # if previously-initialized by the child class, leave alone
        if not hasattr(self, "gui_params"):
            self.gui_params = {}

        scopename = scope.name if scope else "__patch__"

        defaults = dict(obj_id=self.obj_id,
                        initargs=self.init_args, display_type=self.display_type,
                        scope=scopename,
                        num_inlets=inlets, num_outlets=outlets)

        for k, v in defaults.items():
            if k not in self.gui_params:
                self.gui_params[k] = v

        # dsp_inlets and dsp_outlets are the processor inlet/outlet numbers
        # of the ordinal inlets/outlets of the DSP object.
        # for example dsp_outlets = [2] means processor outlet 2
        # corresponds to outlet 0 of the underlying DSP object
        self.dsp_obj = None
        if not hasattr(self, 'dsp_inlets'):
            self.dsp_inlets = []
        if not hasattr(self, 'dsp_outlets'):
            self.dsp_outlets = []

        self.connections_out = [[] for r in range(outlets)]
        self.connections_in = [[] for r in range(inlets)]
        if name is None:
            name = self.display_type
        self.assign(patch, scope, name)

    async def setup(self):
        # called after constructor
        pass

    def info(self):
        log.debug("Object info: obj_id=%d, name=%s, init_type=%s, init_args=%s"
                  % (self.obj_id, self.name, self.init_type, self.init_args))
        return True

    def tooltip(self, port_dir=None, port_num=None, details=False):
        if port_dir == self.PORT_IN:
            if port_num < len(self.doc_tooltip_inlet):
                tip = self.doc_tooltip_inlet[port_num]
            else:
                tip = "No port tip defined"

            if port_num in self.dsp_inlets:
                dsptip = '(~) '
            else:
                dsptip = ''

            if port_num in self.hot_inlets:
                hottip = '(hot) '
            else:
                hottip = ''

            return (('<b>[%(init_type)s] inlet %(port_num)d:</b> ' + dsptip + hottip + tip)
                    % dict(init_type=self.init_type, port_num=port_num))

        elif port_dir == self.PORT_OUT and port_num < len(self.doc_tooltip_outlet):
            if port_num < len(self.doc_tooltip_outlet):
                tip = self.doc_tooltip_outlet[port_num]
            else:
                tip = "No port tip defined"
            if port_num in self.dsp_outlets:
                dsptip = '(~) '
            else:
                dsptip = ''

            return (('<b>[%(init_type)s] outlet %(port_num)d:</b> ' + dsptip + tip)
                    % dict(init_type=self.init_type, port_num=port_num))
        else:
            # basic one-liner
            lines = [('<b>[%s]:</b> ' + self.doc_tooltip_obj) % self.init_type]

            # details for geeks like me
            if details:
                # name and ID
                lines.append('      <b>Name:</b> %s  <b>ID:</b> %s' % (self.name, self.obj_id))
                scopename = ('' if self.scope == self.patch.default_scope
                             else self.scope.name + '.')
                scopedname = '%s%s' % (scopename, self.name)

                lines.append('      <b>Path:</b> %s.%s' % (self.patch.name, scopedname))
                lines.append('          <b>Messages in:</b> %s, <b>Messages out:</b> %s'
                             % (self.count_in, self.count_out))
                lines.append('          <b>Times triggered:</b> %s, <b>Errors:</b> %s'
                             % (self.count_trigger, self.count_errors))
                if self.count_errors:
                    lines.append('          <b>Error messages:</b>')
                    for msg, count in self.error_info.items():
                        lines.append('              %s: %s' % (count, msg))

                if len(self.properties):
                    lines.append('      <b>Properties:</b>')

                    for k, v in self.properties.items():
                        lines.append('          %s -> %s' % (k, v))
                # class-provided extra details
                otherinfo = self.tooltip_extra()
                if otherinfo:
                    if isinstance(otherinfo, str):
                        otherinfo = [otherinfo]
                    for o in otherinfo:
                        if isinstance(o, str):
                            lines.append('      ' + o)

                # OSC controllers
                lines.append('      <b>OSC handlers:</b>')
                minfo = {}
                for m in self.osc_methods:
                    s = minfo.setdefault(m[0], [])
                    s.append(m[1])
                for m in sorted(minfo.keys()):
                    lines.append('          %s %s' % (m, minfo[m]))

                # MIDI controllers
                from .mfp_app import MFPApp
                if self.midi_filters:
                    paths = MFPApp().midi_mgr._filt2paths(self.midi_filters)
                    lines.append('      <b>MIDI handlers:</b>')
                    for p in paths:
                        lines.append('          Chan: %s, Type: %s, Number: %s'
                                     % (p[2] if p[2] is not None else "All",
                                        p[1] if p[1] is not None else "All",
                                        p[3] if p[3] is not None else "All"))
            return '\n'.join(lines)

    def tooltip_extra(self):
        return False

    def call_onload(self, value=True):
        self.do_onload = value

    def onload(self, phase):
        pass

    def assign(self, patch, scope, name):
        # null case
        if (self.patch == patch) and (self.scope == scope) and (self.name == name):
            return

        if self.patch is not None and self.scope is not None and self.name is not None:
            self.patch.unbind(self.name, self.scope)
        elif self.scope is not None and self.name is not None:
            self.scope.unbind(self.name)

        name = name or "%s_%s" % (self.init_type, str(self.obj_id))

        if patch is not None and self.patch is None or self.patch != patch:
            if self.patch:
                self.patch.remove(self)
            self.patch = patch
            self.patch.add(self)

        if scope is not None:
            self.scope = scope
        elif patch is not None:
            self.scope = self.patch.default_scope
        else:
            self.scope = None

        if patch is not None:
            self.name = self.patch.bind(name, self.scope, self)
        elif scope is not None:
            self.name = scope.bind(name, self)
            self.patch = None
        else:
            self.name = name
            self.patch = None

        self.conf(name=self.name, scope=self.scope.name)
        self.osc_init()
        return self.name

    def rename(self, new_name):
        self.assign(self.patch, self.scope, new_name)

    def rescope(self, new_scope):
        if isinstance(new_scope, LexicalScope):
            self.assign(self.patch, new_scope, self.name)
        else:
            self.assign(self.patch, self.patch.scopes.get(new_scope), self.name)

    def _osc_handler(self, path, args, types, src, data):
        if types[0] == 's':
            self.send(self.patch.parse_obj(args[0]))
        else:
            self.send(args[0])

        # return 0 means completely handled, nonzero keep trying
        return 0

    def _osc_learn_handler(self, path, args, types, src, data):
        from .mfp_app import MFPApp
        MFPApp().osc_mgr.del_default(self._osc_learn_handler)
        MFPApp().osc_mgr.add_method(path, types, self._osc_handler)
        self.osc_methods.append((path, types))
        self._osc_handler(path, args, types, src, data)
        self.set_tag("osc", "learned")

    def osc_learn(self):
        from .mfp_app import MFPApp
        MFPApp().osc_mgr.add_default(self._osc_learn_handler)
        self.set_tag("osc", "learning")

    def osc_init(self):
        from .mfp_app import MFPApp

        if MFPApp().osc_mgr is None:
            return

        if self.patch is None:
            patchname = "default"
        else:
            patchname = self.patch.name

        pathbase = "/mfp/%s/%s" % (patchname, self.name)
        o = MFPApp().osc_mgr

        if self.osc_pathbase is not None and self.osc_pathbase != pathbase:
            saved = []
            for m in self.osc_methods:
                if m[0].startswith(self.osc_pathbase):
                    o.del_method(*m)
                else:
                    saved.append(m)
            self.osc_methods = saved
        self.osc_pathbase = pathbase

        for i in range(len(self.inlets)):
            path = "%s/%s" % (pathbase, str(i))
            if path not in self.osc_methods:
                for t in ('s', 'b', 'f'):
                    o.add_method(path, t, self._osc_handler, i)
                    self.osc_methods.append((path, t))

    def _midi_handler(self, event, data):
        from .midi import NoteOff, NoteOn
        if self.midi_mode == "note_bang":
            self.send(Bang)
        elif self.midi_mode == "note_onoff":
            if isinstance(event, NoteOn):
                self.send(True)
            elif isinstance(event, NoteOff):
                self.send(False)
        elif self.midi_mode == "note_vel":
            if isinstance(event, NoteOn):
                self.send(event.velocity)
            elif isinstance(event, NoteOff):
                self.send(0)
        elif self.midi_mode == "cc_val":
            self.send(event.value)
        elif self.midi_mode == "pgm":
            self.send(event.program)
        elif self.midi_mode in ("chan_note", "chan", "note", "cc", "event"):
            self.send(event)

    def _midi_learn_handler(self, event, mode):
        from .mfp_app import MFPApp
        from .midi import Note, NotePress, NoteOff, NoteOn, MidiCC, MidiPgmChange

        filters = {}
        port, etype, channel, unit = event.source()
        port = port[1]

        if mode.startswith("note"):
            if not isinstance(event, NoteOn):
                return
            if mode == "note_bang":
                filters["etype"] = [NoteOn]
            else:
                filters["etype"] = [NoteOn, NoteOff, NotePress]

            filters["channel"] = [channel]
            filters["port"] = [port]
            filters["unit"] = [unit]

        elif mode.startswith("cc"):
            if not isinstance(event, MidiCC):
                return
            filters["etype"] = [type(event)]
            filters["channel"] = [channel]
            filters["port"] = [port]
            filters["unit"] = [unit]

        elif mode.startswith("pgm"):
            if not isinstance(event, MidiPgmChange):
                return
            filters["etype"] = [MidiPgmChange]
            filters["channel"] = [channel]
            filters["port"] = [port]

        elif mode.startswith("chan"):
            if mode == "chan_note":
                if not isinstance(event, NoteOn):
                    return
                filters["etype"] = [NoteOn, NoteOff, NotePress]

            filters["channel"] = [channel]
            filters["port"] = [port]

        elif mode.startswith("auto"):
            if not isinstance(event, (Note, MidiCC, MidiPgmChange)):
                return
            filters["etype"] = [type(event)]
            filters["port"] = [port]
            filters["channel"] = [channel]
            filters["unit"] = [unit]
            if isinstance(event, Note):
                mode = "note_vel"
            elif isinstance(event, MidiCC):
                mode = "cc_val"
            elif isinstance(event, MidiPgmChange):
                mode = "pgm"

        MFPApp().midi_mgr.unregister(self.midi_learn_cbid)
        self.midi_learn_cbid = None
        self.midi_cbid = MFPApp().midi_mgr.register(self._midi_handler, filters=filters)
        self.midi_filters = filters
        self.midi_mode = mode
        self.set_tag("midi", "learned")

    def midi_learn(self, *args, **kwargs):
        from .mfp_app import MFPApp
        mode = kwargs.get("mode", "auto")

        if self.midi_learn_cbid is None:
            if self.midi_cbid is not None:
                MFPApp().midi_mgr.unregister(self.midi_cbid)
                self.midi_cbid = None
            self.midi_learn_cbid = MFPApp().midi_mgr.register(self._midi_learn_handler,
                                                              data=mode)
            self.set_tag("midi", "learning")

    async def dsp_init(self, proc_name, **params):
        from .mfp_app import MFPApp
        if self.patch.context:
            DSPObjectFactory = await MFPApp().rpc_host.require(DSPObject)
            self.dsp_obj = await DSPObjectFactory(
                self.obj_id,
                proc_name,
                len(self.dsp_inlets),
                len(self.dsp_outlets), params,
                self.patch.context,
                self.patch.obj_id
            )
        else:
            log.warning(f"[dsp_init] No DSP context in {self.name}, {proc_name}")
        self.conf(dsp_inlets=self.dsp_inlets, dsp_outlets=self.dsp_outlets)

    def dsp_inlet(self, inlet):
        return (self.dsp_obj, self.dsp_inlets.index(inlet))

    def dsp_outlet(self, outlet):
        return (self.dsp_obj, self.dsp_outlets.index(outlet))

    async def dsp_reset(self):
        await self.dsp_obj.reset()

    async def dsp_setparam(self, param, value):
        await self.dsp_obj.setparam(param, value)

    async def dsp_getparam(self, param, value):
        return await self.dsp_obj.getparam(param, value)

    async def delete(self):
        from .mfp_app import MFPApp
        from .patch import Patch
        if hasattr(self, "patch") and self.patch is not None:
            self.patch.unbind(self.name, self.scope)
            self.patch.remove(self)
        elif isinstance(self, Patch) and self.scope is not None:
            self.scope.unbind(self.name)

        if hasattr(self, "osc_pathbase") and self.osc_pathbase is not None:
            for m, t in self.osc_methods:
                MFPApp().osc_mgr.del_method(m, t)

            self.osc_methods = []
            self.osc_pathbase = None

        if hasattr(self, "connections_out"):
            outport = 0
            for c in self.connections_out:
                to_delete = [pr for pr in c]
                for tobj, tport in to_delete:
                    await self.disconnect(outport, tobj, tport)

                outport += 1

        if hasattr(self, "connections_in"):
            inport = 0
            for c in self.connections_in:
                to_delete = [pr for pr in c]
                for tobj, tport in to_delete:
                    await tobj.disconnect(tport, self, inport)
                inport += 1

        if hasattr(self, "midi_learn_cbid") and self.midi_learn_cbid is not None:
            MFPApp().midi_mgr.unregister(self.midi_learn_cbid)
            self.midi_learn_cbid = None

        if hasattr(self, "midi_cbid") and self.midi_cbid is not None:
            MFPApp().midi_mgr.unregister(self.midi_cbid)
            self.midi_cbid = None

        if hasattr(self, "dsp_obj") and self.dsp_obj is not None:
            if self.patch.context is not None:
                await self.dsp_obj.delete()
            self.dsp_obj = None

        MFPApp().forget(self)
        self.status = self.DELETED

    def resize(self, inlets, outlets):
        inlets = max(inlets, 1)
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
        self.outlet_order = list(range(len(self.outlets)))

        self.conf(num_inlets=inlets, num_outlets=outlets)

    async def connect(self, outlet, target, inlet, show_gui=True):
        from .mfp_app import MFPApp
        from .patch import Patch

        # make sure this is a possibility
        if not isinstance(target, Processor):
            log.warning("Error: Can't connect '%s' (obj_id %d) to %s inlet %d"
                        % (self.name, self.obj_id, target, inlet))
            return False

        if outlet > len(self.outlets):
            log.warning("Error: Can't connect '%s' (obj_id %d) outlet %d (only %d outlets)"
                        % (self.name, self.obj_id, outlet, len(self.outlets)))
            return False

        if inlet > len(target.inlets):
            if isinstance(target, Patch):
                Patch.task_nibbler.add_task(
                    lambda args: Processor.connect(*args), 20,
                    [self, outlet, target, inlet, show_gui])
                log.warning("'%s' (obj_id %d) doesn't have enough inlets (%s/%s), waiting"
                            % (target.name, target.obj_id, len(target.inlets), inlet))
                return True
            else:
                log.warning("Error: Can't connect to '%s' (obj_id %d) inlet %d (only %d inlets)"
                            % (target.name, target.obj_id, inlet, len(target.inlets)))
                return False

        # is this a DSP connection?
        if outlet in self.dsp_outlets:
            if inlet not in target.dsp_inlets:
                if isinstance(target, Patch):
                    Patch.task_nibbler.add_task(
                        lambda args: Processor.connect(*args), 20,
                        [self, outlet, target, inlet, show_gui])
                    log.warning("'%s' (obj_id %d) inlet is not DSP, waiting"
                                % (target.name, target.obj_id))
                    return True
                log.warning(
                    "Error: Can't connect DSP out %s of '%s' to non-DSP in %s of '%s'"
                    % (outlet, self.name, inlet, target.name))
                return False

            out_obj, out_outlet = self.dsp_outlet(outlet)
            in_obj, in_inlet = target.dsp_inlet(inlet)
            if out_obj and in_obj:
                await out_obj.connect(out_outlet, in_obj._id, in_inlet)
            else:
                log.warning("Trying to find DSP objects, failed", type(self), self.name,
                            type(target), target.name,
                            inlet, "-->", in_obj, ",", outlet, "-->", out_obj)

        try:
            existing = self.connections_out[outlet]
            if (target, inlet) not in existing:
                existing.append((target, inlet))
        except Exception:
            # this can happen normally in a creation race, don't
            # flag it (Patch.connect wil retry)
            return False

        existing = target.connections_in[inlet]
        if (self, outlet) not in existing:
            existing.append((self, outlet))

        if (self.gui_created and show_gui and
            self.display_type not in (
                "hidden", "sendvia", "sendsignalvia")
            and target.display_type not in (
                "hidden", "recvvia", "recvsignalvia")):
            task(MFPApp().gui_command.connect(self.obj_id, outlet, target.obj_id, inlet))
        return True

    async def disconnect(self, outlet, target, inlet):
        # is this a DSP connection?
        if outlet in self.dsp_outlets:
            out_obj, out_outlet = self.dsp_outlet(outlet)
            in_obj, in_inlet = target.dsp_inlet(inlet)

            if out_obj is not None and in_obj is not None:
                await out_obj.disconnect(out_outlet, in_obj._id, in_inlet)
            else:
                log.warning("disconnect having trouble,",
                            self, self.name, self.scope, outlet, target, inlet, in_obj,
                            out_obj)

        existing = self.connections_out[outlet]
        if (target, inlet) in existing:
            existing.remove((target, inlet))

        existing = target.connections_in[inlet]
        if (self, outlet) in existing:
            existing.remove((self, outlet))
        return True

    def add_output(self, outlet_num, value):
        if value is Uninit:
            self.outlets[outlet_num] = Uninit
            return

        if self.outlets[outlet_num] is Uninit:
            self.outlets[outlet_num] = value
        else:
            mv = MultiOutput()
            mv.values.append(self.outlets[outlet_num])
            mv.values.append(value)
            self.outlets[outlet_num] = mv

    async def send(self, value, inlet=0):
        if self.paused:
            return

        w_target = None

        try:
            with self.trigger_lock:
                work = await self._send(value, inlet)

            while len(work):
                w_target, w_val, w_inlet = work[0]
                with w_target.trigger_lock:
                    work[:1] = await w_target._send(w_val, w_inlet)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            log.error("%s (%s): send to inlet %d failed: %s" %
                      (self.name, self.init_type, inlet, value))
            log.error("Exception: %s" % e.args)
            log.debug_traceback()
            if w_target:
                w_target.error("%s" % e.args, tb)

    async def _send__activate(self, value, inlet):
        if self.clear_outlets:
            self.outlets = [Uninit] * len(self.outlets)

        if inlet == -1:
            self.dsp_response(value[0], value[1])
        elif isinstance(value, MethodCall):
            self.method(value, inlet)
        elif isinstance(value, AsyncOutput):
            if value.outlet_num not in range(len(self.outlets)):
                log.error("_send: object %s has no outlet '%s'" % (self.name,
                                                                   value.outlet_num))
            else:
                self.add_output(value.outlet_num, value.value)
                self.inlets[inlet] = Uninit
        else:
            await self.trigger()
            self.count_trigger += 1

    async def _send__propagate(self):
        output_pairs = list(zip(self.connections_out, self.outlets))
        work = []

        for conns, val in [output_pairs[i] for i in self.outlet_order]:
            if val is Uninit:
                continue

            if isinstance(val, LazyExpr):
                val = val.call()
            if isinstance(val, MultiOutput):
                values = val.values
            else:
                values = [val]

            for val in values:
                self.count_out += 1
                for target, tinlet in conns:
                    if target is not None:
                        if self.patch.step_debugger.enabled:
                            self.patch.step_debugger.add_task(
                                self._send__propagate_value(target, val, tinlet)
                            )
                        else:
                            work.append((target, val, tinlet))
                    else:
                        log.warning("Bad output connection: obj_id=%s" % self.obj_id)
        return work

    async def _send__propagate_value(self, target, val, inlet):
        with target.trigger_lock:
            return await target._send(val, inlet)

    async def _send__dsp_params(self, value, inlet):
        try:
            await self.dsp_obj.setparam("_sig_" + str(inlet), float(value))
        except (TypeError, ValueError):
            pass

    async def _send__initiate(self, value, inlet):
        self.inlets[inlet] = value

    async def _send(self, value, inlet=0):
        if self.paused:
            return []

        work = []
        if inlet >= 0:
            if self.patch.step_debugger.enabled:
                self.patch.step_debugger.add_task(self._send__initiate(value, inlet))
            else:
                await self._send__initiate(value, inlet)

        self.count_in += 1

        if inlet in self.hot_inlets or inlet == -1:
            if self.patch.step_debugger.enabled:
                self.patch.step_debugger.add_task(self._send__activate(value, inlet))
                self.patch.step_debugger.add_task(self._send__propagate())
            else:
                await self._send__activate(value, inlet)
                work = await self._send__propagate()

        if (
            (inlet in self.dsp_inlets)
            and not isinstance(value, bool)
            and isinstance(value, (float, int))
        ):
            if self.patch.step_debugger.enabled:
                self.patch.step_debugger.add_task(self._send__dsp_params(value, inlet))
            else:
                await self._send__dsp_params(value, inlet)

        return work

    def parse_args(self, pystr, **extra_bindings):
        from .patch import Patch
        if "scope" not in extra_bindings:
            extra_bindings["scope"] = self.scope
        if "__self__" not in extra_bindings:
            extra_bindings["__self__"] = self
        if "__patch__" not in extra_bindings:
            extra_bindings["__patch__"] = self.patch

        if isinstance(self, Patch):
            return self.evaluator.eval_arglist(pystr, **extra_bindings)
        elif self.patch:
            return self.patch.parse_args(pystr, **extra_bindings)
        else:
            from .evaluator import Evaluator
            e = Evaluator()
            return e.eval_arglist(pystr, **extra_bindings)

    def parse_obj(self, pystr, **extra_bindings):
        from .patch import Patch
        if "scope" not in extra_bindings:
            extra_bindings["scope"] = self.scope
        if "__self__" not in extra_bindings:
            extra_bindings["__self__"] = self
        if "__patch__" not in extra_bindings:
            extra_bindings["__patch__"] = self.patch

        if isinstance(self, Patch):
            return self.evaluator.eval(pystr, **extra_bindings)
        elif self.patch:
            return self.patch.parse_obj(pystr, **extra_bindings)
        else:
            from .evaluator import Evaluator
            e = Evaluator()
            return e.eval(pystr, **extra_bindings)

    def method(self, message, inlet):
        '''Default method handler ignores which inlet the message was received on'''
        message.call(self)
        self.inlets[inlet] = Uninit

    def reset_counts(self):
        self.count_in = 0
        self.count_out = 0
        self.count_errors = 0
        self.error_info = {}
        self.count_trigger = 0
        self.set_tag("errorcount", self.count_errors)

    def error(self, msg=None, tb=None):
        from .mfp_app import MFPApp
        self.count_errors += 1
        self.set_tag("errorcount", self.count_errors)

        if msg:
            self.error_info[msg] = self.error_info.get(msg, 0) + 1

        if MFPApp().debug:
            for tbline in tb.strip().split('\n'):
                log.debug(tbline)

    def create_gui(self, **kwargs):
        from .mfp_app import MFPApp
        parent_id = self.patch.obj_id if self.patch is not None else None
        for param, value in kwargs.items():
            self.gui_params[param] = value

        if kwargs.get('is_export'):
            xoff = (
                self.patch.gui_params.get('export_frame_xoff', 2)
                - (self.patch.gui_params.get('export_x') or 0)
            )

            self.gui_params['export_offset_x'] = xoff
            self.gui_params['position_x'] += xoff
            yoff = (
                self.gui_params.get('export_frame_yoff', 20)
                - (self.patch.gui_params.get('export_y') or 0)
            )

            self.gui_params['export_offset_y'] = yoff
            self.gui_params['position_y'] += yoff

        task(
            MFPApp().gui_command.create(self.init_type, self.init_args, self.obj_id,
                                        parent_id, self.gui_params)
        )
        self.gui_created = True

    async def delete_gui(self):
        from .mfp_app import MFPApp
        await MFPApp().gui_command.delete(self.obj_id)
        self.gui_created = False

    def conf(self, **kwargs):
        from .mfp_app import MFPApp
        for k, v in kwargs.items():
            self.gui_params[k] = v
        if self.gui_created:
            task(MFPApp().gui_command.configure(self.obj_id, **kwargs))

    def set_tag(self, tag, value):
        self.tags[tag] = value
        self.conf(tags=self.tags)

    def set_style(self, tag, value):
        oldstyle = self.gui_params.get('style', {})
        oldstyle[tag] = value
        self.conf(style=oldstyle)

    def mark_ready(self):
        self.status = Processor.READY

    def property(self, *args, **kwargs):
        if len(kwargs):
            for key, value in kwargs.items():
                self.properties[key] = value
            return None
        elif len(args):
            return [self.properties.get(a) for a in args]
        else:
            return []

    def property_delete(self, *args):
        for a in args:
            if a in self.properties:
                del self.properties[a]

    async def clone(self, patch, scope, name):
        from .mfp_app import MFPApp
        prms = self.save()

        newobj = await MFPApp().create(prms.get("type"), prms.get("initargs"),
                                       patch, scope, name)
        newobj.load(prms)
        return newobj

    # save/restore helper
    def save(self):
        '''
        Save object state to a dictionary suitable for serialization

        Custom behavior in subclasses should call Processor.save()
        first, then modify the dictionary that it returns.
        '''

        oinfo = {}
        oinfo['type'] = self.init_type
        oinfo['initargs'] = self.init_args
        oinfo['name'] = self.name
        oinfo['do_onload'] = self.do_onload
        oinfo['gui_params'] = {}

        oinfo['properties'] = self.properties
        oinfo['midi_filters'] = self.midi_filters
        oinfo['midi_mode'] = self.midi_mode

        nonstd_osc = []
        for o in self.osc_methods:
            if not o[0].startswith(self.osc_pathbase):
                nonstd_osc.append(o)

        oinfo['osc_methods'] = nonstd_osc

        for k, v in self.gui_params.items():
            if k not in ['name', 'obj_id', 'dsp_inlets', 'dsp_outlets', 'num_inlets',
                         'num_outlets']:
                oinfo['gui_params'][k] = v

        conn = []
        for c in self.connections_out:
            conn.append([(t[0].obj_id, t[1]) for t in c])
        oinfo['connections'] = conn
        return oinfo

    def load(self, prms):
        '''
        Initialize a Processor from a dictionary returned by save()

        Custom behavior in Processor subclasses must call Processor.load,
        probably before anything else.
        '''

        from .mfp_app import MFPApp

        # special handling for gui_params
        gp = prms.get('gui_params')

        for k, v in gp.items():
            self.gui_params[k] = v
        self.gui_params['scope'] = self.scope.name

        # these are needed at runtime but don't get saved
        self.gui_params["obj_id"] = self.obj_id
        self.gui_params["name"] = self.name
        self.gui_params["dsp_inlets"] = self.dsp_inlets
        self.gui_params["dsp_outlets"] = self.dsp_outlets
        self.gui_params["num_inlets"] = len(self.inlets)
        self.gui_params["num_outlets"] = len(self.outlets)

        self.do_onload = prms.get('do_onload', False)
        self.properties = prms.get('properties', {})

        # set up saved OSC controllers
        for path, types in prms.get("osc_methods", []):
            MFPApp().osc_mgr.add_method(path, types, self._osc_handler)
            self.osc_methods.append((path, types))

        # and MIDI
        self.midi_mode = prms.get("midi_mode", None)
        self.midi_filters = prms.get("midi_filters", None)
        if self.midi_filters is not None:
            ports = self.midi_filters.get("port", [])
            if not isiterable(ports):
                ports = [ports]

            self.midi_filters["port"] = [tuple(p) for p in ports]
            self.midi_cbid = MFPApp().midi_mgr.register(self._midi_handler,
                                                        filters=self.midi_filters)
