#! /usr/bin/env python
'''
midi.py: MIDI handling for MFP

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import asyncio
from threading import Lock
from datetime import datetime
import alsaseq
from .utils import QuittableThread
from . import appinfo
from . import lv2midi
from . import log
from .utils import isiterable
from .patch_json import ext_encode


@ext_encode
class SeqEvent:
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


def mk_raw(event, port=0):
    raw = [0, 0, 0, 0, (0, 0), (0, port), (0, 0)]
    if event.seqevent is not None:
        raw[0] = int(event.seqevent.etype)
        raw[1] = int(event.seqevent.flags)
        raw[2] = int(event.seqevent.tag)
        raw[3] = int(event.seqevent.queue)
        raw[4] = event.seqevent.timestamp
        raw[5] = event.seqevent.src
        raw[6] = event.seqevent.dst
    else:
        raw[0] = int(event.seq_type())

    raw.append(event.seq_data())
    return tuple(raw)


@ext_encode
class MidiEvent:
    _lv2_registry = {}
    alsa_type = None

    def __init__(self, seqevent=None):
        self.seqevent = seqevent
        self.channel = 1
        self.client = None
        self.port = 0

        if self.seqevent:
            if self.seqevent.dst:
                self.client = self.seqevent.dst[0]
                self.port = self.seqevent.dst[1]
            self.channel = seqevent.data[0] + 1
            self.timestamp = self.seqevent.timestamp

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'lv2_type'):
            MidiEvent._lv2_registry[cls.lv2_type] = cls

    def source(self):
        return (self.seqevent.dst, self.seqevent.etype, self.channel, None)

    def seq_type(self):
        if self.seqevent is not None:
            return self.seqevent.etype
        return self.alsa_type

    def from_lv2(self, msg):
        etype = lv2midi.lv2_midi_message_type(msg)
        ctor = MidiEvent._lv2_registry.get(etype)
        if ctor:
            ev = ctor()
            ev.from_lv2(msg)
            return ev
        return self

    def to_lv2(self):
        return 0

    def seq_data(self):
        if self.seqevent is not None:
            return self.seqevent.data
        return ()


@ext_encode
class MidiUndef (MidiEvent):
    def __repr__(self):
        return "<MidiUndef %s>" % self.seqevent


@ext_encode
class Note (MidiEvent):
    alsa_type = alsaseq.SND_SEQ_EVENT_NOTE

    def __init__(self, seqevent=None):
        super().__init__(seqevent)
        self.key = 0
        self.velocity = 0

        if self.seqevent is not None:
            self.key = seqevent.data[1]
            self.velocity = seqevent.data[2]

    def seq_data(self):
        return (self.channel-1, self.key, self.velocity, 0, 0)


@ext_encode
class NoteOn (Note):
    alsa_type = alsaseq.SND_SEQ_EVENT_NOTEON
    lv2_type = lv2midi.LV2_MIDI_MSG_NOTE_ON

    def __init__(self, seqevent=None):
        super().__init__(seqevent)
        self.key = 0
        self.velocity = 0

        if self.seqevent is not None:
            self.key = seqevent.data[1]
            self.velocity = seqevent.data[2]

    def source(self):
        return (self.seqevent.dst, NoteOn.__name__, self.channel, self.key)

    def from_lv2(self, msg):
        self.key = (msg & 0xff0000) >> 16
        self.velocity = (msg & 0xff00) >> 8
        self.channel = msg & 0xff

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | (self.key << 16) | (self.velocity << 8) | self.channel
        )

    def __repr__(self):
        return "<NoteOn %s %s %s>" % (self.channel, self.key, self.velocity)


@ext_encode
class NoteOff (Note):
    alsa_type = alsaseq.SND_SEQ_EVENT_NOTEOFF
    lv2_type = lv2midi.LV2_MIDI_MSG_NOTE_OFF

    def __init__(self, seqevent=None):
        super().__init__(seqevent)
        self.key = 0
        self.velocity = 0

        if self.seqevent is not None:
            self.key = seqevent.data[1]
            self.velocity = seqevent.data[2]

    def seq_data(self):
        return (self.channel-1, self.key, 0, self.velocity, 0)

    def source(self):
        return (self.seqevent.dst, NoteOff.__name__, self.channel, self.key)

    def from_lv2(self, msg):
        self.key = (msg & 0xff0000) >> 16
        self.velocity = (msg & 0xff00) >> 8
        self.channel = msg & 0xff

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | (self.key << 16) | (self.velocity << 8) | self.channel
        )

    def __repr__(self):
        return "<NoteOff %s %s %s>" % (self.channel, self.key, self.velocity)


@ext_encode
class NotePress (Note):
    lv2_type = lv2midi.LV2_MIDI_MSG_NOTE_PRESSURE

    def __init__(self, seqevent=None):
        super().__init__(seqevent)
        self.key = 0
        self.velocity = 0

        if self.seqevent is not None:
            if self.seqevent.etype == alsaseq.SND_SEQ_EVENT_KEYPRESS:
                self.key = seqevent.data[1]
                self.velocity = seqevent.data[2]
            elif self.seqevent.etype == alsaseq.SND_SEQ_EVENT_CHANPRESS:
                self.velocity = seqevent.data[2]

    def source(self):
        return (self.seqevent.dst, NotePress.__name__, self.channel, self.key)

    def from_lv2(self, msg):
        self.key = (msg & 0xff0000) >> 16
        self.velocity = (msg & 0xff00) >> 8
        self.channel = msg & 0xff

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | (self.key << 16) | (self.velocity << 8) | self.channel
        )

    def __repr__(self):
        return "<NotePress %s %s %s>" % (self.channel, self.key, self.velocity)


@ext_encode
class ChannelPress (NotePress):
    lv2_type = lv2midi.LV2_MIDI_MSG_CHANNEL_PRESSURE


@ext_encode
class MidiPgmChange (MidiEvent):
    alsa_type = alsaseq.SND_SEQ_EVENT_PGMCHANGE
    lv2_type = lv2midi.LV2_MIDI_MSG_PGM_CHANGE

    def __init__(self, seqevent=None):
        super().__init__(seqevent)
        self.program = None

        if self.seqevent is not None:
            self.program = seqevent.data[5]

    def seq_data(self):
        return (self.channel-1, 0, 0, 0, 0, self.program)

    def source(self):
        return (self.seqevent.dst, MidiPgmChange.__name__, self.channel, None)

    def from_lv2(self, msg):
        self.program = (msg & 0xff0000) >> 16
        self.channel = msg & 0xff

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | (self.program << 16) | self.channel | self.channel
        )

    def __repr__(self):
        return "<MidiPgmChange %s %s>" % (self.channel, self.program)


@ext_encode
class MidiCC (MidiEvent):
    alsa_type = alsaseq.SND_SEQ_EVENT_CONTROLLER
    lv2_type = lv2midi.LV2_MIDI_MSG_CONTROLLER

    def __init__(self, seqevent=None):
        super().__init__(seqevent)
        self.controller = 0
        self.value = 0

        if self.seqevent is not None:
            self.controller = seqevent.data[4]
            self.value = seqevent.data[5]

    def seq_data(self):
        return (self.channel-1, 0, 0, 0, self.controller, self.value)

    def source(self):
        return (self.seqevent.dst, MidiCC.__name__, self.channel, self.controller)

    def from_lv2(self, msg):
        self.controller = (msg & 0xff0000) >> 16
        self.value = (msg & 0xff00) >> 8
        self.channel = msg & 0xff

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | (self.controller << 16) | (self.value << 8) | self.channel
        )

    def __repr__(self):
        return "<MidiCC %s %s %s>" % (self.channel, self.controller, self.value)


@ext_encode
class MidiPitchbend (MidiCC):
    alsa_type = alsaseq.SND_SEQ_EVENT_PITCHBEND
    lv2_type = lv2midi.LV2_MIDI_MSG_BENDER

    def __init__(self, seqevent=None):
        super().__init__(seqevent)
        self.note = 0
        self.value = 0

        if self.seqevent is not None:
            self.note = seqevent.data[1]
            self.value = seqevent.data[5]

    def seq_data(self):
        return (self.channel-1, self.note, 0, 0, 1, self.value)

    def source(self):
        return (self.seqevent.dst, MidiPitchbend.__name__, self.channel, self.note)

    def from_lv2(self, msg):
        self.note = (msg & 0xff0000) >> 16
        self.value = (msg & 0xff00) >> 8
        self.channel = msg & 0xff

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | (self.note << 16) | (self.value << 8) | self.channel
        )

    def __repr__(self):
        return "<MidiPitchbend %s %s %s>" % (self.channel, self.note, self.value)


@ext_encode
class MidiClock(MidiEvent):
    alsa_type = alsaseq.SND_SEQ_EVENT_CLOCK
    lv2_type = lv2midi.LV2_MIDI_MSG_CLOCK

    def from_lv2(self, msg):
        self.channel = msg & 0xff

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | self.channel
        )


@ext_encode
class MidiQFrame(MidiEvent):
    alsa_type = alsaseq.SND_SEQ_EVENT_QFRAME
    lv2_type = lv2midi.LV2_MIDI_MSG_MTC_QUARTER

    def __init__(self, seqevent=None):
        super().__init__(seqevent)
        if seqevent:
            payload = seqevent.data[5]
            self.field = payload & 0xf0 >> 4
            self.value = payload & 0xf0

    def from_lv2(self, msg):
        self.field = 0
        self.value = 0
        self.channel = msg & 0xff

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | self.channel
        )


@ext_encode
class MidiStart(MidiEvent):
    alsa_type = alsaseq.SND_SEQ_EVENT_START
    lv2_type = lv2midi.LV2_MIDI_MSG_START

    def from_lv2(self, msg):
        self.channel = msg & 0xff

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | self.channel
        )


@ext_encode
class MidiStop(MidiEvent):
    alsa_type = alsaseq.SND_SEQ_EVENT_STOP
    lv2_type = lv2midi.LV2_MIDI_MSG_STOP

    def from_lv2(self, msg):
        self.channel = msg & 0xff

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | self.channel
        )


@ext_encode
class MidiContinue(MidiEvent):
    alsa_type = alsaseq.SND_SEQ_EVENT_CONTINUE
    lv2_type = lv2midi.LV2_MIDI_MSG_CONTINUE

    def from_lv2(self, msg):
        self.channel = msg & 0xff

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | self.channel
        )


@ext_encode
class MidiSPP(MidiEvent):
    alsa_type = alsaseq.SND_SEQ_EVENT_SONGPOS
    lv2_type = lv2midi.LV2_MIDI_MSG_SONG_POS

    def __init__(self, seqevent=None):
        super().__init__(seqevent)
        if seqevent and len(seqevent.data) == 6:
            self.position = seqevent.data[5]
        else:
            self.position = 0

    def from_lv2(self, msg):
        self.position = (msg & 0xffff00) >> 8
        self.channel = msg & 0xff

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | (self.position << 8) | self.channel
        )

    def __repr__(self):
        return "<MidiSPP %s %s>" % (self.channel, self.position)


@ext_encode
class MidiSysex(MidiEvent):
    alsa_type = alsaseq.SND_SEQ_EVENT_SYSEX
    lv2_type = lv2midi.LV2_MIDI_MSG_SYSTEM_EXCLUSIVE

    def __init__(self, seqevent=None):
        super().__init__(seqevent)

    def from_lv2(self, msg):
        self.channel = msg & 0xff


def from_alsaseq(raw_event):
    etypemap = {
        alsaseq.SND_SEQ_EVENT_SYSTEM: MidiUndef,
        alsaseq.SND_SEQ_EVENT_RESULT: MidiUndef,
        alsaseq.SND_SEQ_EVENT_NOTE: MidiUndef,   # length encoding?
        alsaseq.SND_SEQ_EVENT_NOTEON: NoteOn,
        alsaseq.SND_SEQ_EVENT_NOTEOFF: NoteOff,
        alsaseq.SND_SEQ_EVENT_KEYPRESS: NotePress,
        alsaseq.SND_SEQ_EVENT_CONTROLLER: MidiCC,
        alsaseq.SND_SEQ_EVENT_PGMCHANGE: MidiPgmChange,
        alsaseq.SND_SEQ_EVENT_CHANPRESS: NotePress,
        alsaseq.SND_SEQ_EVENT_PITCHBEND: MidiPitchbend,
        alsaseq.SND_SEQ_EVENT_CONTROL14: MidiUndef,
        alsaseq.SND_SEQ_EVENT_NONREGPARAM: MidiUndef,
        alsaseq.SND_SEQ_EVENT_REGPARAM: MidiUndef,
        alsaseq.SND_SEQ_EVENT_SONGPOS: MidiSPP,
        alsaseq.SND_SEQ_EVENT_SONGSEL: MidiUndef,
        alsaseq.SND_SEQ_EVENT_QFRAME: MidiQFrame,
        alsaseq.SND_SEQ_EVENT_TIMESIGN: MidiUndef,
        alsaseq.SND_SEQ_EVENT_KEYSIGN: MidiUndef,
        alsaseq.SND_SEQ_EVENT_START: MidiStart,
        alsaseq.SND_SEQ_EVENT_CONTINUE: MidiContinue,
        alsaseq.SND_SEQ_EVENT_STOP: MidiStop,
        alsaseq.SND_SEQ_EVENT_SETPOS_TICK: MidiUndef,
        alsaseq.SND_SEQ_EVENT_SETPOS_TIME: MidiUndef,
        alsaseq.SND_SEQ_EVENT_TEMPO: MidiUndef,
        alsaseq.SND_SEQ_EVENT_CLOCK: MidiClock,
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
        alsaseq.SND_SEQ_EVENT_SYSEX: MidiSysex,
        alsaseq.SND_SEQ_EVENT_BOUNCE: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR_VAR0: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR_VAR1: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR_VAR2: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR_VAR3: MidiUndef,
        alsaseq.SND_SEQ_EVENT_USR_VAR4: MidiUndef,
        alsaseq.SND_SEQ_EVENT_NONE: MidiUndef
    }

    ctor = etypemap.get(raw_event[0])
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


def from_lv2(raw_event):
    etypemap = {
        lv2midi.LV2_MIDI_MSG_INVALID: MidiUndef,
        lv2midi.LV2_MIDI_MSG_NOTE_OFF: NoteOff,
        lv2midi.LV2_MIDI_MSG_NOTE_ON: NoteOn,
        lv2midi.LV2_MIDI_MSG_NOTE_PRESSURE: NotePress,
        lv2midi.LV2_MIDI_MSG_CONTROLLER: MidiCC,
        lv2midi.LV2_MIDI_MSG_PGM_CHANGE: MidiPgmChange,
        lv2midi.LV2_MIDI_MSG_CHANNEL_PRESSURE: NotePress,
        lv2midi.LV2_MIDI_MSG_BENDER: MidiPitchbend,
        lv2midi.LV2_MIDI_MSG_SYSTEM_EXCLUSIVE: MidiUndef,
        lv2midi.LV2_MIDI_MSG_MTC_QUARTER: MidiUndef,
        lv2midi.LV2_MIDI_MSG_SONG_POS: MidiUndef,
        lv2midi.LV2_MIDI_MSG_SONG_SELECT: MidiUndef,
        lv2midi.LV2_MIDI_MSG_TUNE_REQUEST: MidiUndef,
        lv2midi.LV2_MIDI_MSG_CLOCK: MidiUndef,
        lv2midi.LV2_MIDI_MSG_START: MidiUndef,
        lv2midi.LV2_MIDI_MSG_CONTINUE: MidiUndef,
        lv2midi.LV2_MIDI_MSG_STOP: MidiUndef,
        lv2midi.LV2_MIDI_MSG_ACTIVE_SENSE: MidiUndef,
        lv2midi.LV2_MIDI_MSG_RESET: MidiUndef,
    }

    lv2_type = (raw_event & 0xff000000) >> 24
    ctor = etypemap.get(lv2_type)
    if ctor is None:
        log.debug("midi: no constructor for", raw_event)
        ctor = MidiUndef
    ev = ctor()
    ev.parse_lv2(raw_event)
    return ev


class MFPMidiManager(QuittableThread):

    def __init__(self, inports, outports):
        self.num_inports = inports
        self.num_outports = outports
        self.start_time = None
        self.event_loop = asyncio.get_event_loop()
        self.handlers_by_id = {}
        self.handlers_by_filter = {None: {None: {None: {None: []}}}}
        self.handlers_lock = Lock()
        self.handlers_next_id = 0

        QuittableThread.__init__(self)

    def _filt2paths(self, filters):
        ports = filters.get("port") or [None]
        typeinfos = filters.get("etype") or [None]
        channels = filters.get("channel") or [None]
        units = filters.get("unit") or [None]
        paths = []

        if not isiterable(ports):
            ports = [ports]
        if not isiterable(typeinfos):
            typeinfos = [typeinfos]
        if not isiterable(channels):
            channels = [channels]
        if not isiterable(units):
            units = [units]

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
        import copy
        from .utils import isiterable
        if filters is None:
            filters = {}

        if "etype" in filters:
            old = filters.get("etype")
            if not isiterable(old):
                old = [old]
            filters["etype"] = [
                e.__name__
                if isinstance(e, type) else e
                for e in old
            ]

        with self.handlers_lock:
            cb_id = self.handlers_next_id
            self.handlers_next_id += 1
            self.handlers_by_id[cb_id] = (cb_id, callback, copy.copy(filters), data)
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
        return None

    def run(self):
        import select

        alsaseq.client(appinfo.name, self.num_inports, self.num_outports, True)
        self.start_time = datetime.now()
        alsaseq.start()
        log.debug("ALSA sequencer started")

        alsafd = alsaseq.fd()
        while not self.join_req:
            select.select([alsafd], [], [], 0.1)
            if alsaseq.inputpending():
                raw_event = alsaseq.input()
                new_event = from_alsaseq(raw_event)
                self.dispatch_event(new_event)
        alsaseq.stop()
        alsaseq.close()

    def dispatch_event(self, event):
        port, typeinfo, channel, unit = event.source()
        port = port[1]

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
                except Exception as e:
                    log.debug("Error in MIDI event handler:", e)

    def send(self, port, event):
        from datetime import datetime, timedelta
        starttime = datetime.now()

        raw_tuple = mk_raw(event, port)
        try:
            alsaseq.output(raw_tuple)
        except Exception as e:
            log.debug("alsaseq: error on output of", raw_tuple, e)
            log.debug_traceback(e)

        elapsed = datetime.now() - starttime

        if elapsed > timedelta(microseconds=2000):
            log.debug("MIDI send took %s milliseconds" % elapsed.total_seconds() * 1000)
