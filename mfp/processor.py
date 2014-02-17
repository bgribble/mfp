#! /usr/bin/env python
'''
processor.py: Parent class of all processors

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from .dsp_object import DSPObject
from .method import MethodCall
from .bang import Uninit, Bang
from .scope import LexicalScope

from . import log

class Processor (object):
    PORT_IN = 0 
    PORT_OUT = 1

    CTOR = 0 
    READY = 1 
    ERROR = 2
    DELETED = 3 

    display_type = 'processor'
    save_to_patch = True 
    hot_inlets = [0]

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
        self.outlet_order = range(outlets)
        self.status = Processor.CTOR
        self.tags = {} 
        self.name = None
        self.patch = None
        self.scope = None
        self.osc_pathbase = None
        self.osc_methods = []
        self.count_in = 0
        self.count_out = 0
        self.count_trigger = 0 
        self.count_errors = 0 
        self.midi_mode = None 
        self.midi_filters = None 
        self.midi_cbid = None 
        self.midi_learn_cbid = None 

        self.gui_created = False
        self.do_onload = True 

        # gui_params are passed back and forth to the UI process
        # if previously-initialized by the child class, leave alone
        if not hasattr(self, "gui_params"):
            self.gui_params = {}

        defaults = dict(obj_id=self.obj_id, 
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
        if not hasattr(self, 'dsp_inlets'):
            self.dsp_inlets = []
        if not hasattr(self, 'dsp_outlets'):
            self.dsp_outlets = []

        self.connections_out = [[] for r in range(outlets)]
        self.connections_in = [[] for r in range(inlets)]
        if name is None:
            name = self.display_type 
        self.assign(patch, scope, name)

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

            return (('<b>[%s] inlet %d:</b> ' + dsptip + hottip + tip)
                    % (self.init_type, port_num))

        elif port_dir == self.PORT_OUT and port_num < len(self.doc_tooltip_outlet):
            if port_num < len(self.doc_tooltip_outlet):
                tip = self.doc_tooltip_outlet[port_num]
            else: 
                tip = "No port tip defined"
            if port_num in self.dsp_outlets: 
                dsptip = '(~) '
            else: 
                dsptip = ''

            return (('<b>[%s] outlet %d:</b> ' + dsptip + tip) % (self.init_type, port_num))
        else: 
            # basic one-liner 
            lines = [ ('<b>[%s]:</b> ' + self.doc_tooltip_obj) % self.init_type ]

            # details for geeks like me 
            if details: 
                # name and ID 
                lines.append('      <b>Name:</b> %s  <b>ID:</b> %s' % (self.name, self.obj_id))
                lines.append('          <b>Messages in:</b> %s, <b>Messages out:</b> %s'
                             % (self.count_in, self.count_out))
                lines.append('          <b>Times triggered:</b> %s, <b>Errors:</b> %s'
                             % (self.count_trigger, self.count_errors))
                # class-provided extra details 
                otherinfo = self.tooltip_extra()
                if otherinfo:
                    if isinstance(otherinfo, str):
                        otherinfo = [ otherinfo ]
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

        self.gui_params["name"] = self.name 
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

        if mode.startswith("note"):
            if not isinstance(event, NoteOn):
                return 
            if mode == "note_bang":
                filters["etype"] = [ NoteOn ]
            else:
                filters["etype"] = [ NoteOn, NoteOff, NotePress ]

            filters["channel"] = [channel] 
            filters["port"] = [port] 
            filters["unit"] = [unit] 

        elif mode.startswith("cc"):
            if not isinstance(event, MidiCC):
                return 
            filters["etype"] = [ type(event) ]
            filters["channel"] = [channel]
            filters["port"] = [port]
            filters["unit"] = [unit]

        elif mode.startswith("pgm"):
            if not isinstance(event, MidiPgmChange):
                return 
            filters["etype"] = [ MidiPgmChange ]
            filters["channel"] = [channel]
            filters["port"] = [port]

        elif mode.startswith("chan"):
            if mode == "chan_note":
                if not isinstance(event, NoteOn):
                    return 
                filters["etype"] = [ NoteOn, NoteOff, NotePress ]

            filters["channel"] = [channel]
            filters["port"] = [port]

        elif mode.startswith("auto"):
            if not isinstance(event, (Note, MidiCC, MidiPgmChange)):
                return 
            filters["etype"] = [ type(event) ]
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

    def dsp_init(self, proc_name, **params):
        from .mfp_app import MFPApp
        self.dsp_obj = DSPObject(self.obj_id, proc_name, len(self.dsp_inlets),
                                 len(self.dsp_outlets), params)
        self.gui_params['dsp_inlets'] = self.dsp_inlets
        self.gui_params['dsp_outlets'] = self.dsp_outlets
        if self.gui_created:
            MFPApp().gui_command.configure(self.obj_id, self.gui_params)

    def dsp_inlet(self, inlet):
        return (self.dsp_obj, self.dsp_inlets.index(inlet))

    def dsp_outlet(self, outlet):
        return (self.dsp_obj, self.dsp_outlets.index(outlet))

    def dsp_reset(self):
        self.dsp_obj.reset()

    def dsp_setparam(self, param, value):
        self.dsp_obj.setparam(param, value)

    def dsp_getparam(self, param, value):
        return self.dsp_obj.getparam(param, value)

    def delete(self):
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
                for tobj, tport in c:
                    self.disconnect(outport, tobj, tport)
                outport += 1

        if hasattr(self, "connections_in"):
            inport = 0
            for c in self.connections_in:
                for tobj, tport in c:
                    tobj.disconnect(tport, self, inport)
                inport += 1

        if hasattr(self, "midi_learn_cbid") and self.midi_learn_cbid is not None:
            MFPApp().midi_mgr.unregister(self.midi_learn_cbid)
            self.midi_learn_cbid = None 

        if hasattr(self, "midi_cbid") and self.midi_cbid is not None:
            MFPApp().midi_mgr.unregister(self.midi_cbid)
            self.midi_cbid = None 

        if hasattr(self, "dsp_obj") and self.dsp_obj is not None:
            self.dsp_obj.delete()
            self.dsp_obj = None

        MFPApp().forget(self)
        self.status = self.DELETED 

    def resize(self, inlets, outlets):
        from .mfp_app import MFPApp
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
            MFPApp().gui_command.configure(self.obj_id, self.gui_params)

    def connect(self, outlet, target, inlet):
        # make sure this is a possibility 
        if not isinstance(target, Processor):
            log.debug("Error: Can't connect '%s' (obj_id %d) to %s inlet %d"
                      % (self.name, self.obj_id, target, inlet))
            return False 

        if outlet > len(self.outlets):
            log.debug("Error: Can't connect '%s' (obj_id %d) outlet %d (only %d outlets)"
                      % (self.name, self.obj_id, outlet, len(self.outlets)))
            return False 
        
        if inlet > len(target.inlets):
            log.debug("Error: Can't connect to '%s' (obj_id %d) inlet %d (only %d inlets)"
                      % (target.name, target.obj_id, inlet, len(target.inlets)))
            return False 

        # is this a DSP connection?
        if outlet in self.dsp_outlets:
            if inlet not in target.dsp_inlets: 
                log.debug("Error: Can't connect DSP outlet %s of '%s' to non-DSP inlet %s of '%s'" 
                          % (outlet, self.name, inlet, target.name))
                return False 

            out_obj, out_outlet = self.dsp_outlet(outlet)
            in_obj, in_inlet = target.dsp_inlet(inlet)

            out_obj.connect(out_outlet, in_obj.obj_id, in_inlet)

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
            out_obj, out_outlet = self.dsp_outlet(outlet)
            in_obj, in_inlet = target.dsp_inlet(inlet)

            out_obj.disconnect(out_outlet, in_obj.obj_id, in_inlet)

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
        except Exception, e:
            log.debug("Exception: " + e.message)
            log.debug("%s %s: send to inlet %d failed: %s" % (self.init_type, self.name, inlet,
                                                           value))
            import traceback
            tb = traceback.format_exc()
            self.error(tb)

    def _send(self, value, inlet=0):
        work = []
        if inlet >= 0:
            self.inlets[inlet] = value

        self.count_in += 1 

        if inlet in self.hot_inlets or inlet == -1:
            self.outlets = [Uninit] * len(self.outlets)
            if inlet == -1:
                self.dsp_response(value[0], value[1])
            elif isinstance(value, MethodCall):
                self.method(value, inlet)
            else:
                self.trigger()
                self.count_trigger += 1
            output_pairs = zip(self.connections_out, self.outlets)

            for conns, val in [output_pairs[i] for i in self.outlet_order]:
                if val is not Uninit:
                    self.count_out += 1
                    for target, tinlet in conns:
                        if target is not None:
                            work.append((target, val, tinlet))
                        else:
                            log.debug("Bad output connection: obj_id=%s" % self.obj_id)
        try:
            if ((inlet in self.dsp_inlets) 
                and not isinstance(value, bool) and isinstance(value, (float,int))):
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

    def reset_counts(self):
        from .mfp_app import MFPApp
        self.count_in = 0
        self.count_out = 0
        self.count_errors = 0
        self.count_trigger = 0
        self.set_tag("errorcount", self.count_errors)
        if self.gui_created:
            MFPApp().gui_command.configure(self.obj_id, self.gui_params)


    def error(self, tb=None):
        self.count_errors += 1
        self.set_tag("errorcount", self.count_errors)

        print "Error:", self
        if tb:
            print tb

    def create_gui(self):
        from .mfp_app import MFPApp
        parent_id = self.patch.obj_id if self.patch is not None else None 
        MFPApp().gui_command.create(self.init_type, self.init_args, self.obj_id,
                                    parent_id, self.gui_params)
        self.gui_created = True

    def delete_gui(self):
        from .mfp_app import MFPApp
        MFPApp().gui_command.delete(self.obj_id)
        self.gui_created = False

    def set_tag(self, tag, value): 
        from .mfp_app import MFPApp
        self.tags[tag] = value 
        self.gui_params["tags"] = self.tags
        if self.gui_created:
            MFPApp().gui_command.configure(self.obj_id, self.gui_params)

    def mark_ready(self):
        self.status = Processor.READY

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

        oinfo['midi_filters'] = self.midi_filters
        oinfo['midi_mode'] = self.midi_mode 

        nonstd_osc = [] 
        for o in self.osc_methods:
            if not o[0].startswith(self.osc_pathbase):
                nonstd_osc.append(o)

        oinfo['osc_methods' ] = nonstd_osc

        for k, v in self.gui_params.items():
            if k not in [ 'name', 'obj_id', 'dsp_inlets', 'dsp_outlets', 'num_inlets', 
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

        # these are needed at runtime but don't get saved 
        self.gui_params["obj_id"] = self.obj_id
        self.gui_params["name"] = self.name 
        self.gui_params["dsp_inlets"] = self.dsp_inlets
        self.gui_params["dsp_outlets"] = self.dsp_outlets
        self.gui_params["num_inlets"] = len(self.inlets)
        self.gui_params["num_outlets"] = len(self.outlets)

        self.do_onload = prms.get('do_onload', False)

        # set up saved OSC controllers 
        for path, types in prms.get("osc_methods", []):
            MFPApp().osc_mgr.add_method(path, types, self._osc_handler)
            self.osc_methods.append((path, types))

        # and MIDI 
        self.midi_mode = prms.get("midi_mode", None)
        self.midi_filters = prms.get("midi_filters", None)
        if self.midi_filters is not None:
            ports = self.midi_filters.get("port")
            self.midi_filters["port"] = [ tuple(p) for p in ports ]
            self.midi_cbid = MFPApp().midi_mgr.register(self._midi_handler, 
                                                        filters=self.midi_filters)
