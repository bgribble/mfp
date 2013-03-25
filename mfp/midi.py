#! /usr/bin/env python2.7
'''
midi.py: MIDI handling for MFP

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import alsaseq
from quittable_thread import QuittableThread
from threading import Lock 
from datetime import datetime
from . import appinfo

from . import log


class SeqEvent(object):
    def __init__(self, etype, flags, tag, queue, timestamp, src, dst, data):
        self.etype = etype
        self.flags = flags
        self.tag = tag
        self.queue = queue
        self.timestamp = timestamp
        self.src = src
        self.dst = dst
        self.data = data

    def __repr__(self): 
        return "<SeqEvent 0x%02x 0x%02x %s>" % (self.etype, self.flags, self.data)

class MidiUndef (object):
    def __init__(self, seqevent=None):
        self.seqevent = seqevent
        self.channel = seqevent.data[0] 

    def source(self):
        return (self.seqevent.dst, self.seqevent.etype, self.channel, None)

    def __repr__(self):
        return "<MidiUndef %s>" % self.seqevent


class Note (object):
    pass


class NoteOn (Note):
    def __init__(self, seqevent=None):
        self.seqevent = seqevent
        self.channel = None
        self.key = None
        self.velocity = None

        if self.seqevent is not None:
            self.channel = seqevent.data[0]
            self.key = seqevent.data[1]
            self.velocity = seqevent.data[2]

    def source(self):
        return (self.seqevent.dst, NoteOn, self.channel, self.key)

    def __repr__(self):
        return "<NoteOn %s %s %s>" % (self.channel, self.key, self.velocity)


class NoteOff (Note):
    def __init__(self, seqevent=None):
        self.seqevent = seqevent
        self.channel = None
        self.key = None
        self.velocity = None

        if self.seqevent is not None:
            self.channel = seqevent.data[0]
            self.key = seqevent.data[1]
            self.velocity = seqevent.data[2]

    def source(self):
        return (self.seqevent.dst, NoteOff, self.channel, self.key)

    def __repr__(self):
        return "<NoteOff %s %s %s>" % (self.channel, self.key, self.velocity)

class NotePress (Note): 
    def __init__(self, seqevent=None):
        self.seqevent = seqevent
        self.channel = None
        self.key = None
        self.pressure = None

        if self.seqevent is not None:
            if self.seqevent.etype == alsaseq.SND_SEQ_EVENT_NOTEPRESS:
                self.channel = seqevent.data[0]
                self.key = seqevent.data[1]
                self.pressure = seqevent.data[2]
            elif self.seqevent.etype == alsaseq.SND_SEQ_EVENT_CHANPRESS:
                self.channel = seqevent.data[0]
                self.pressure = seqevent.data[2]

    def source(self):
        return (self.seqevent.dst, NotePress, self.channel, self.key)

    def __repr__(self):
        return "<NotePress %s %s %s>" % (self.channel, self.key, self.pressure)

class MidiPgmChange (object): 
    def __init__(self, seqevent=None):
        self.seqevent = seqevent
        self.channel = None 
        self.program = None 

        if self.seqevent is not None:
            self.channel = seqevent.data[0]
            self.program = seqevent.data[5]

    def source(self):
        return (self.seqevent.dst, MidiPgmChange, self.channel, None)

    def __repr__(self):
        return "<MidiPgmChange %s %s>" % (self.channel, self.program)

class MidiCC (object):
    def __init__(self, seqevent=None):
        self.seqevent = seqevent
        self.channel = None
        self.controller = None
        self.value = None

        if self.seqevent is not None:
            self.channel = seqevent.data[0]
            self.controller = seqevent.data[4]
            self.value = seqevent.data[5]

    def source(self):
        return (self.seqevent.dst, MidiCC, self.channel, self.controller)

    def __repr__(self):
        return "<MidiCC %s %s %s>" % (self.channel, self.controller, self.value)

class MFPMidiManager(QuittableThread):
    etypemap = {
        alsaseq.SND_SEQ_EVENT_SYSTEM: MidiUndef,
        alsaseq.SND_SEQ_EVENT_RESULT: MidiUndef,
        alsaseq.SND_SEQ_EVENT_NOTE: MidiUndef,
        alsaseq.SND_SEQ_EVENT_NOTEON: NoteOn,
        alsaseq.SND_SEQ_EVENT_NOTEOFF: NoteOff,
        alsaseq.SND_SEQ_EVENT_KEYPRESS: NotePress,
        alsaseq.SND_SEQ_EVENT_CONTROLLER: MidiCC,
        alsaseq.SND_SEQ_EVENT_PGMCHANGE: MidiPgmChange,
        alsaseq.SND_SEQ_EVENT_CHANPRESS: NotePress,

        alsaseq.SND_SEQ_EVENT_CONTROL14: MidiUndef,
        alsaseq.SND_SEQ_EVENT_NONREGPARAM: MidiUndef,
        alsaseq.SND_SEQ_EVENT_REGPARAM: MidiUndef,
        alsaseq.SND_SEQ_EVENT_SONGPOS: MidiUndef,
        alsaseq.SND_SEQ_EVENT_SONGSEL: MidiUndef,
        alsaseq.SND_SEQ_EVENT_QFRAME: MidiUndef,
        alsaseq.SND_SEQ_EVENT_TIMESIGN: MidiUndef,
        alsaseq.SND_SEQ_EVENT_KEYSIGN: MidiUndef,
        alsaseq.SND_SEQ_EVENT_START: MidiUndef,
        alsaseq.SND_SEQ_EVENT_CONTINUE: MidiUndef,
        alsaseq.SND_SEQ_EVENT_STOP: MidiUndef,
        alsaseq.SND_SEQ_EVENT_SETPOS_TICK: MidiUndef,
        alsaseq.SND_SEQ_EVENT_SETPOS_TIME: MidiUndef,
        alsaseq.SND_SEQ_EVENT_TEMPO: MidiUndef,
        alsaseq.SND_SEQ_EVENT_CLOCK: MidiUndef,
        alsaseq.SND_SEQ_EVENT_TICK: MidiUndef,
        alsaseq.SND_SEQ_EVENT_QUEUE_SKEW: MidiUndef,
        alsaseq.SND_SEQ_EVENT_SYNC_POS: MidiUndef,
        alsaseq.SND_SEQ_EVENT_TUNE_REQUEST: MidiUndef,
        alsaseq.SND_SEQ_EVENT_RESET: MidiUndef,
        alsaseq.SND_SEQ_EVENT_SENSING: MidiUndef,
        alsaseq.SND_SEQ_EVENT_ECHO: MidiUndef,
        alsaseq.SND_SEQ_EVENT_OSS: MidiUndef,
        alsaseq.SND_SEQ_EVENT_CLIENT_START: MidiUndef,
        alsaseq.SND_SEQ_EVENT_CLIENT_EXIT: MidiUndef,
        alsaseq.SND_SEQ_EVENT_CLIENT_CHANGE: MidiUndef,
        alsaseq.SND_SEQ_EVENT_PORT_START: MidiUndef,
        alsaseq.SND_SEQ_EVENT_PORT_EXIT: MidiUndef,
        alsaseq.SND_SEQ_EVENT_PORT_CHANGE: MidiUndef,
        alsaseq.SND_SEQ_EVENT_PORT_SUBSCRIBED: MidiUndef,
        alsaseq.SND_SEQ_EVENT_PORT_UNSUBSCRIBED: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR0: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR1: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR2: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR3: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR4: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR5: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR6: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR7: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR8: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR9: MidiUndef,
        alsaseq.SND_SEQ_EVENT_SYSEX: MidiUndef,
        alsaseq.SND_SEQ_EVENT_BOUNCE: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR_VAR0: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR_VAR1: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR_VAR2: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR_VAR3: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR_VAR4: MidiUndef,
        alsaseq.SND_SEQ_EVENT_NONE: MidiUndef
    }

    def __init__(self, inports, outports):
        self.num_inports = inports
        self.num_outports = outports
        self.start_time = None
        self.handlers_by_id = {} 
        self.handlers_by_filter = { None: { None: { None: { None: [] }}}}
        self.handlers_lock = Lock() 
        self.handlers_next_id = 0

        QuittableThread.__init__(self)

    def _filt2paths(self, filters):
        ports = filters.get("port") or [ None ] 
        typeinfos = filters.get("etype") or [ None ] 
        channels = filters.get("channel") or [ None ] 
        units = filters.get("unit") or [ None ] 
        paths = [] 

        for port in ports: 
            for typeinfo in typeinfos:
                for channel in channels: 
                    for unit in units: 
                        paths.append((port, typeinfo, channel, unit))

        return paths 

    
    def _savepath(self, path, value):
        typeinfo = self.handlers_by_filter.setdefault(path[0], {})
        chaninfo = typeinfo.setdefault(path[1], {})
        unitinfo = chaninfo.setdefault(path[2], {})
        dest = unitinfo.setdefault(path[3], [])
        dest.append(value)

    def _delpath(self, path, value):
        typeinfo = self.handlers_by_filter.setdefault(path[0], {})
        chaninfo = typeinfo.setdefault(path[1], {})
        unitinfo = chaninfo.setdefault(path[2], {})
        dest = unitinfo.setdefault(path[3], [])
        if value in dest: 
            dest.remove(value)


    def register(self, callback, data=None, filters=None):
        if filters == None:
            filters = {} 

        with self.handlers_lock:
            cb_id = self.handlers_next_id
            self.handlers_next_id += 1 

            self.handlers_by_id[cb_id] = (cb_id, callback, filters, data) 
            paths = self._filt2paths(filters)
            for p in paths: 
                self._savepath(p, cb_id)

        return cb_id

    def unregister(self, cb_id):
        cbinfo = self.handlers_by_id.get(cb_id)
        if cbinfo is None:
            return None

        cb_id, callback, filters, data = cbinfo
        paths = self._filt2paths(filters)
        for p in paths: 
            self._delpath(p, cb_id)


    def run(self):
        import select

        alsaseq.client(appinfo.name, self.num_inports, self.num_outports, True)
        self.start_time = datetime.now()
        alsaseq.start()
        log.debug("ALSA sequencer started")

        alsafd = alsaseq.fd()
        while not self.join_req:
            fds_ready = select.select([alsafd], [], [], 0.1)
            if alsaseq.inputpending():
                raw_event = alsaseq.input()
                new_event = self.create_event(raw_event)
                self.dispatch_event(new_event)

    def create_event(self, raw_event):
        ctor = self.etypemap.get(raw_event[0])
        if ctor is None:
            log.debug("midi: no constructor for", raw_event)
            ctor = MidiUndef
        # special case for NoteOn with velocity 0 -- it's a NoteOff,
        # treat it as such
        elif ctor is NoteOn:
            non = ctor(SeqEvent(*raw_event))
            if non.velocity == 0:
                return NoteOff(SeqEvent(*raw_event))
        return ctor(SeqEvent(*raw_event))

    def dispatch_event(self, event):
        port, typeinfo, channel, unit = event.source()  

        handlers = [] 
        port_by_name = None if port is None else self.handlers_by_filter.get(port) 
        port_default = self.handlers_by_filter.get(None) 

        for portdict in port_by_name, port_default: 
            if portdict is None:
                continue 
            type_by_name = None if typeinfo is None else portdict.get(typeinfo) 
            type_default = portdict.get(None)

            for typedict in type_by_name, type_default: 
                if typedict is None:
                    continue 
                channel_by_name = None if channel is None else typedict.get(channel)
                channel_default = typedict.get(None)

                for chandict in channel_by_name, channel_default:
                    if chandict is None:
                        continue 
                    unit_by_name = None if unit is None else chandict.get(unit)
                    unit_default = chandict.get(None)

                    for unitlist in unit_by_name, unit_default:
                        if not unitlist:
                            continue 
                        handlers.extend(unitlist)

        # now handlers should have all the relevant (cb_id, callback) pairs  
        for h in handlers: 
            cbinfo = self.handlers_by_id.get(h)
            if cbinfo is not None:
                cb_id, callback, filters, data = cbinfo
                try:
                    callback(event, data)
                except Exception, e: 
                    log.debug("Error in MIDI event handler:", e)

    def send(self, port, data):
        pass
