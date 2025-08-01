#! /usr/bin/env python
'''
p_midi.py: builtins for MIDI I/O

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import asyncio
import copy

from mfp import log
from .. import Bang, Uninit
from ..processor import Processor
from ..mfp_app import MFPApp
from ..method import MethodCall
from ..midi import (
    Note, NoteOn, NoteOff, NotePress,
    MidiCC, MidiPgmChange, MidiUndef,
    MidiClock, MidiPitchbend, MidiStart, MidiStop, MidiContinue,
    MidiQFrame, MidiSysex, MidiSPP, MidiTimeSignature
)

event_types = (
    Note, NoteOn, NoteOff, NotePress,
    MidiCC, MidiPgmChange, MidiClock, MidiPitchbend, MidiStart, MidiStop, MidiContinue,
    MidiQFrame, MidiSysex, MidiSPP, MidiUndef, MidiTimeSignature
)


class MidiIn (Processor):
    doc_tooltip_obj = "Receive MIDI events from ALSA sequencer"
    doc_tooltip_inlet = ["Config/MIDI passthru input"]
    doc_tooltip_outlet = ["MIDI event output"]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name, defs)

        self.port = 0
        self.channels = []

        extra = defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)

        if kwargs:
            self.handler = MFPApp().midi_mgr.register(
                lambda event, data: asyncio.run_coroutine_threadsafe(
                    self.send(event, data),
                    MFPApp().midi_mgr.event_loop
                ),
                0, kwargs
            )
            self.midi_filters = copy.copy(kwargs)
        else:
            self.handler = MFPApp().midi_mgr.register(
                lambda event, data: asyncio.run_coroutine_threadsafe(
                    self.send(event, data),
                    MFPApp().midi_mgr.event_loop
                ),
                0
            )

    def filter(self, **filters):
        MFPApp().midi_mgr.unregister(self.handler)
        self.handler = MFPApp().midi_mgr.register(
            lambda event, data: asyncio.create_task(self.send(event, data)),
            0, filters
        )
        self.midi_filters = copy.copy(filters)

    async def trigger(self):
        event = self.inlets[0]
        if isinstance(event, dict):
            for attr, val in event.items():
                setattr(self, attr, val)
        elif isinstance(event, MethodCall):
            self.method(event, 0)
        elif isinstance(event, event_types):
            self.outlets[0] = event
        else:
            log.debug(f"[midi_in] unmatched {event}")

class MidiOut (Processor):
    doc_tooltip_obj = "Send MIDI events to ALSA sequencer"
    doc_tooltip_inlet = ["Config/MIDI data input"]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 1, 0, init_type, init_args, patch, scope, name, defs)
        self.port = 0
        self.channel = None

        extra = defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)
        if len(initargs):
            self.channel = initargs[0]

    async def trigger(self):
        event = self.inlets[0]

        if isinstance(event, dict):
            for attr, val in event.items():
                setattr(self, attr, val)
        elif isinstance(event, MethodCall):
            self.method(event, 0)
        elif isinstance(event, event_types):
            event.port = self.port
            if self.channel is not None:
                event.channel = self.channel
            await MFPApp().midi_mgr.send(self.port, event)


class MidiTime (Processor):
    doc_tooltip_obj = "Assemble MIDI and MTC events into full time output"
    doc_tooltip_inlet = ["MIDI data input"]
    doc_tooltip_outlet = [
        "SMPTE time HH:MM:SS:FF",
        "Song position bar:beat:clock",
    ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 1, 2, init_type, init_args, patch, scope, name, defs)
        self.frame_rate_values = [
            "24", "24", "30 drop", "30"
        ]
        self.frame_time = [0, 0, 0, 0]
        self.frame_rate = "30"
        self.partial_time = [0, 0, 0, 0]  # hours, minutes, seconds, frames
        self.partial_fields = set()

        self.spp_beats_per_measure = 4
        self.spp_beats_per_quarter = 1

        self.spp_reset_pending = False
        self.spp_position = 0  # in quarter notes
        self.clock_count = 0   # in 24 PPQN

    def _bbm_pos(self):
        total_beats = self.spp_position // self.spp_beats_per_quarter
        bars = total_beats // self.spp_beats_per_measure
        beats = total_beats % self.spp_beats_per_measure
        return [bars + 1, beats + 1, self.clock_count]

    async def trigger(self):
        event = self.inlets[0]

        if event == Bang:
            self.outlets[0] = self.frame_time
            self.outlets[1] = self._bbm_pos()

        if isinstance(event, MidiQFrame):
            field = event.field
            value = event.value

            if field == 0:
                self.partial_time = [0, 0, 0, 0]
                self.partial_fields = set()

            self.partial_fields.add(field)

            if field in (1, 3, 5):
                value = value << 4
            elif field == 7:
                value = (value & 0x01) << 4
                self.frame_rate = self.frame_rate_values[value & 0x06]
            field = 3 - field // 2

            self.partial_time[field] = self.partial_time[field] + value

            if event.field == 7 and self.partial_fields == set([0, 1, 2, 3, 4, 5, 6, 7]):
                self.frame_time = self.partial_time
                self.outlets[0] = self.frame_time

        if isinstance(event, MidiStart):
            self.spp_reset_pending = False
            self.spp_position = 0
            self.clock_count = 0
            self.outlets[1] = self._bbm_pos()

        if isinstance(event, MidiStop):
            self.spp_reset_pending = True

        if isinstance(event, MidiSPP):
            self.spp_reset_pending = False
            self.spp_position = event.position // 4
            self.clock_count = (event.position % 4) * 8
            self.outlets[1] = self._bbm_pos()

        if isinstance(event, MidiContinue):
            self.spp_reset_pending = False
            self.outlets[1] = self._bbm_pos()

        if isinstance(event, MidiClock):
            if self.spp_reset_pending:
                self.spp_reset_pending = False
                self.spp_position = 0
                self.clock_count = 0
                self.outlets[1] = self._bbm_pos()
            else:
                self.clock_count += 1
                if self.clock_count >= 24:
                    self.clock_count = self.clock_count - 24
                    self.spp_position += 1
                    self.outlets[1] = self._bbm_pos()

        if isinstance(event, MidiTimeSignature):
            log.debug("[midi_time] signature = {event.value}")


def register():
    MFPApp().register("midi_in", MidiIn)
    MFPApp().register("midi_out", MidiOut)
    MFPApp().register("midi_time", MidiTime)

    MFPApp().register("midi.in", MidiIn)
    MFPApp().register("midi.out", MidiOut)
    MFPApp().register("midi.time", MidiTime)
