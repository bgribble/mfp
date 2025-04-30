#! /usr/bin/env python
'''
midi.py: MIDI handling for MFP

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import asyncio
from threading import Lock
from datetime import datetime
import alsa_midi
from . import lv2midi
from . import log
from .utils import isiterable
from .patch_json import ext_encode


class LV2MidiEvent:
    def __init__(self, raw_value):
        self.value = raw_value

@ext_encode
class MidiEvent:
    _lv2_registry = {}
    _alsa_registry = {}

    alsa_type = None
    lv2_type = None

    def __init__(self, event=None):
        self.event = event
        self.channel = 1
        self.source = None
        self.dest = None

        if self.event and isinstance(self.event, alsa_midi.Event):
            self.from_alsaseq(self.event)
        elif self.event and isinstance(self.event, LV2MidiEvent):
            self.from_lv2(self.event)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'lv2_type'):
            MidiEvent._lv2_registry[cls.lv2_type] = cls
        if hasattr(cls, 'alsa_type'):
            MidiEvent._alsa_registry[cls.alsa_type] = cls

    def seq_type(self):
        if self.event is not None:
            return self.event.etype
        return self.alsa_type

    def from_alsaseq(self, seqevent):
        self.source = seqevent.source
        self.dest = seqevent.dest
        self.channel = None
        if hasattr(seqevent, 'channel'):
            self.channel = seqevent.channel
        self.timestamp = seqevent.time

    def to_alsaseq(self):
        return None

    def from_lv2(self, msg):
        self.channel = msg.value & 0xff

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | self.channel
        )


@ext_encode
class MidiUndef (MidiEvent):
    def __repr__(self):
        return "<MidiUndef %s>" % self.event


@ext_encode
class Note (MidiEvent):
    alsa_type = alsa_midi.EventType.NOTE

    def __init__(self, seqevent=None):
        self.key = 0
        self.velocity = 0
        self.duration = 0
        super().__init__(seqevent)

    def from_alsaseq(self, seqevent):
        super().from_alsaseq(seqevent)
        self.key = seqevent.note
        self.velocity = seqevent.velocity
        if hasattr(seqevent, 'duration'):
            self.duration = seqevent.duration

    def to_alsaseq(self):
        return alsa_midi.NoteEvent(
            channel=self.channel,
            note=self.key,
            velocity=self.velocity,
            duration=self.duration,
        )

    def seq_data(self):
        return (self.channel-1, self.key, self.velocity, 0, 0)


@ext_encode
class NoteOn (Note):
    alsa_type = alsa_midi.EventType.NOTEON
    lv2_type = lv2midi.LV2_MIDI_MSG_NOTE_ON

    def __init__(self, seqevent=None):
        self.key = 0
        self.velocity = 0

        super().__init__(seqevent)

    def source(self):
        return (self.event.dst, NoteOn.__name__, self.channel, self.key)

    def from_alsaseq(self, seqevent):
        super().from_alsaseq(seqevent)
        self.key = seqevent.note
        self.velocity = seqevent.velocity

    def to_alsaseq(self):
        return alsa_midi.NoteOnEvent(
            channel=self.channel,
            note=self.key,
            velocity=self.velocity,
        )
    def from_lv2(self, msg):
        super().from_lv2(msg)
        self.key = (msg & 0xff0000) >> 16
        self.velocity = (msg & 0xff00) >> 8

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | (self.key << 16) | (self.velocity << 8) | self.channel
        )

    def __repr__(self):
        return "<NoteOn %s %s %s>" % (self.channel, self.key, self.velocity)


@ext_encode
class NoteOff (Note):
    alsa_type = alsa_midi.EventType.NOTEOFF
    lv2_type = lv2midi.LV2_MIDI_MSG_NOTE_OFF

    def __init__(self, seqevent=None):
        self.key = 0
        self.velocity = 0
        super().__init__(seqevent)

    def seq_data(self):
        return (self.channel-1, self.key, 0, self.velocity, 0)

    def source(self):
        return (self.event.dst, NoteOff.__name__, self.channel, self.key)

    def from_alsaseq(self, seqevent):
        super().from_alsaseq(seqevent)
        self.key = seqevent.note
        self.velocity = seqevent.velocity

    def to_alsaseq(self):
        return alsa_midi.NoteOffEvent(
            channel=self.channel,
            note=self.key,
            velocity=self.velocity,
        )

    def from_lv2(self, msg):
        super().from_lv2(msg)
        self.key = (msg & 0xff0000) >> 16
        self.velocity = (msg & 0xff00) >> 8

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | (self.key << 16) | (self.velocity << 8) | self.channel
        )

    def __repr__(self):
        return "<NoteOff %s %s %s>" % (self.channel, self.key, self.velocity)


@ext_encode
class NotePress (Note):
    lv2_type = lv2midi.LV2_MIDI_MSG_NOTE_PRESSURE
    alsa_type = alsa_midi.EventType.KEYPRESS

    def __init__(self, seqevent=None):
        self.key = -1
        self.velocity = 0
        super().__init__(seqevent)

    def source(self):
        return (self.event.dst, NotePress.__name__, self.channel, self.key)

    def from_alsaseq(self, seqevent):
        super().from_alsaseq(seqevent)
        if seqevent.type == alsa_midi.EventType.KEYPRESS:
            self.key = seqevent.note
            self.velocity = seqevent.velocity
        elif seqevent.type == alsa_midi.EventType.CHANPRESS:
            self.velocity = seqevent.velocity

    def to_alsaseq(self):
        if self.key >= 0:
            return alsa_midi.KeyPressureEvent(
                channel=self.channel,
                note=self.key,
                velocity=self.velocity,
            )
        else:
            return alsa_midi.ChannelPressureEvent(
                channel=self.channel,
                velocity=self.velocity,
            )

    def from_lv2(self, msg):
        super().from_lv2(msg)
        self.key = (msg & 0xff0000) >> 16
        self.velocity = (msg & 0xff00) >> 8

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | (self.key << 16) | (self.velocity << 8) | self.channel
        )

    def __repr__(self):
        return "<NotePress %s %s %s>" % (self.channel, self.key, self.velocity)


@ext_encode
class ChannelPress (NotePress):
    lv2_type = lv2midi.LV2_MIDI_MSG_CHANNEL_PRESSURE
    alsa_type = alsa_midi.EventType.CHANPRESS


@ext_encode
class MidiPgmChange (MidiEvent):
    alsa_type = alsa_midi.EventType.PGMCHANGE
    lv2_type = lv2midi.LV2_MIDI_MSG_PGM_CHANGE

    def __init__(self, seqevent=None):
        super().__init__(seqevent)
        self.program = None

    def seq_data(self):
        return (self.channel-1, 0, 0, 0, 0, self.program)

    def source(self):
        return (self.event.dst, MidiPgmChange.__name__, self.channel, None)

    def from_alsaseq(self, seqevent):
        super().from_alsaseq(seqevent)
        self.program = seqevent.value

    def to_alsaseq(self):
        return alsa_midi.ProgramChangeEvent(channel=self.channel, value=self.program)

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
    alsa_type = alsa_midi.EventType.CONTROLLER
    lv2_type = lv2midi.LV2_MIDI_MSG_CONTROLLER

    def __init__(self, seqevent=None):
        super().__init__(seqevent)
        self.controller = 0
        self.value = 0

    def seq_data(self):
        return (self.channel-1, 0, 0, 0, self.controller, self.value)

    def source(self):
        return (self.event.dst, MidiCC.__name__, self.channel, self.controller)

    def from_alsaseq(self, seqevent):
        super().from_alsaseq(seqevent)
        self.controller = seqevent.param
        self.value = seqevent.value

    def to_alsaseq(self):
        return alsa_midi.ControlChangeEvent(
            channel=self.channel, param=self.controller, value=self.value
        )

    def from_lv2(self, msg):
        super().from_lv2(msg)
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
class MidiPitchbend (MidiEvent):
    alsa_type = alsa_midi.EventType.PITCHBEND
    lv2_type = lv2midi.LV2_MIDI_MSG_BENDER

    def __init__(self, seqevent=None):
        super().__init__(seqevent)
        self.value = 0

    def seq_data(self):
        return (self.channel-1, self.note, 0, 0, 1, self.value)

    def source(self):
        return (self.event.dst, MidiPitchbend.__name__, self.channel, self.note)

    def from_alsaseq(self, seqevent):
        super().from_alsaseq(seqevent)
        self.value = seqevent.value

    def to_alsaseq(self):
        return alsa_midi.PitchBendEvent(channel=self.channel, value=self.value)

    def from_lv2(self, msg):
        super().from_lv2(msg)
        self.value = (msg & 0xff0000) >> 16
        self.channel = msg & 0xff

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | (self.value << 16) | self.channel
        )

    def __repr__(self):
        return "<MidiPitchbend %s %s>" % (self.channel, self.value)


@ext_encode
class MidiClock(MidiEvent):
    alsa_type = alsa_midi.EventType.CLOCK
    lv2_type = lv2midi.LV2_MIDI_MSG_CLOCK

    def to_alsaseq(self):
        return alsa_midi.ClockEvent()


@ext_encode
class MidiQFrame(MidiEvent):
    alsa_type = alsa_midi.EventType.QFRAME
    lv2_type = lv2midi.LV2_MIDI_MSG_MTC_QUARTER

    def __init__(self, seqevent=None):
        self.field = 0
        self.value = 0
        super().__init__(seqevent)

    def from_alsaseq(self, seqevent):
        super().from_alsaseq(seqevent)
        payload = seqevent.raw_data[8]
        self.field = payload & 0xf0 >> 4
        self.value = payload & 0xf0

    def to_alsaseq(self):
        databytes = [0] * 12
        databytes[8] = (self.field << 4) | self.value
        return alsa_midi.Event(type=self.alsa_type, raw_data=bytes(bytearray(databytes)))

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
    alsa_type = alsa_midi.EventType.START
    lv2_type = lv2midi.LV2_MIDI_MSG_START

    def to_alsaseq(self):
        return alsa_midi.StartEvent()


@ext_encode
class MidiStop(MidiEvent):
    alsa_type = alsa_midi.EventType.STOP
    lv2_type = lv2midi.LV2_MIDI_MSG_STOP

    def to_alsaseq(self):
        return alsa_midi.StopEvent()


@ext_encode
class MidiContinue(MidiEvent):
    alsa_type = alsa_midi.EventType.CONTINUE
    lv2_type = lv2midi.LV2_MIDI_MSG_CONTINUE

    def to_alsaseq(self):
        return alsa_midi.ContinueEvent()


@ext_encode
class MidiSPP(MidiEvent):
    alsa_type = alsa_midi.EventType.SONGPOS
    lv2_type = lv2midi.LV2_MIDI_MSG_SONG_POS

    def __init__(self, seqevent=None):
        self.position = 0
        super().__init__(seqevent)

    def from_alsaseq(self, seqevent):
        super().from_alsaseq(seqevent)
        self.position = seqevent.value

    def from_lv2(self, msg):
        super().from_lv2(msg)
        self.position = (msg & 0xffff00) >> 8
        self.channel = msg & 0xff

    def to_lv2(self):
        return (
            (self.lv2_type << 24) | (self.position << 8) | self.channel
        )

    def __repr__(self):
        return "<MidiSPP %s %s>" % (self.channel, self.position)


@ext_encode
class MidiTimeSignature(MidiEvent):
    alsa_type = alsa_midi.EventType.TIMESIGN
    #lv2_type = lv2midi.LV2_MIDI_MSG_SONG_POS

    def __init__(self, seqevent=None):
        self.value = 0
        super().__init__(seqevent)

    def from_alsaseq(self, seqevent):
        super().from_alsaseq(seqevent)
        self.value = seqevent.value

    def __repr__(self):
        return "<MidiTimeSignature %s %s>" % (self.channel, self.value)


@ext_encode
class MidiSysex(MidiEvent):
    alsa_type = alsa_midi.EventType.SYSEX
    lv2_type = lv2midi.LV2_MIDI_MSG_SYSTEM_EXCLUSIVE

    def __init__(self, seqevent=None):
        self.data = None
        super().__init__(seqevent)

    def from_alsaseq(self, seqevent):
        super().from_alsaseq(seqevent)
        self.data = seqevent.data

    def from_lv2(self, msg):
        super().from_lv2(msg)


def from_alsaseq(raw_event):
    ctor = MidiEvent._alsa_registry.get(raw_event.type, MidiUndef)

    # special case for NoteOn with velocity 0 -- it's a NoteOff,
    # treat it as such
    if ctor is NoteOn:
        if raw_event.velocity == 0:
            return NoteOff(raw_event)

    return ctor(raw_event)


def from_lv2(raw_event):
    lv2_type = lv2midi.lv2_midi_message_type(raw_event)
    ctor = MidiEvent._lv2_registry.get(lv2_type, MidiUndef)
    ev = ctor(LV2MidiEvent(raw_event))
    return ev


class MFPMidiManager:

    def __init__(self, inports, outports):
        self.num_inports = inports
        self.num_outports = outports
        self.start_time = None
        self.event_loop = asyncio.get_event_loop()
        self.handlers_by_id = {}
        self.handlers_by_filter = {None: {None: {None: {None: []}}}}
        self.handlers_lock = Lock()
        self.handlers_next_id = 0

        self.client = None
        self.input_ports = []
        self.output_ports = []

        self.quit_req = False

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

    async def run(self):
        self.start_time = datetime.now()

        self.client = alsa_midi.AsyncSequencerClient("mfpmain")
        for portnum in range(self.num_inports):
            self.input_ports.append(
                self.client.create_port(
                    f"mfp_in_{portnum}",
                    caps=alsa_midi.WRITE_PORT,
                    type=alsa_midi.PortType.APPLICATION,
                )
            )

        for portnum in range(self.num_outports):
            self.output_ports.append(
                self.client.create_port(
                    f"mfp_out_{portnum}",
                    caps=alsa_midi.READ_PORT,
                    type=alsa_midi.PortType.APPLICATION,
                )
            )

        log.debug("ALSA sequencer started")

        while not self.quit_req:
            event = await self.client.event_input()
            if event:
                mfp_event = from_alsaseq(event)
                self.dispatch_event(mfp_event)

        self.client.close()

    def finish(self):
        self.quit_req = True

    def dispatch_event(self, event):
        port = event.source.port_id
        unit = event.source.client_id
        channel = event.channel
        typeinfo = None

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

    async def send(self, portnum, event):
        from datetime import datetime, timedelta
        starttime = datetime.now()

        try:
            port = self.output_ports[portnum]
            seq_event = event.to_alsaseq()
            if seq_event:
                seq_event.tick = 0
                seq_event.relative = True
                await self.client.event_output(seq_event, port=port)
                await self.client.drain_output()
            elapsed = datetime.now() - starttime

            if elapsed > timedelta(microseconds=3000):
                log.debug(f"[midi] send took {elapsed.total_seconds()*1000} milliseconds")

        except Exception as e:
            log.debug("[midi] error on output of", event, e)
            log.debug_traceback(e)

