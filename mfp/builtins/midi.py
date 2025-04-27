#! /usr/bin/env python
'''
p_midi.py: builtins for MIDI I/O

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import asyncio
import copy

from ..processor import Processor
from ..mfp_app import MFPApp
from ..method import MethodCall
from ..midi import (
    Note, NoteOn, NoteOff, NotePress,
    MidiCC, MidiPgmChange, MidiUndef,
    MidiClock, MidiStart, MidiStop, MidiContinue, MidiQFrame, MidiSysex, MidiSPP
)

event_types = (
    Note, NoteOn, NoteOff, NotePress,
    MidiCC, MidiPgmChange, MidiClock, MidiStart, MidiStop, MidiContinue,
    MidiQFrame, MidiSysex, MidiSPP, MidiUndef
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


class MidiOut (Processor):
    doc_tooltip_obj = "Send MIDI events to ALSA sequencer"
    doc_tooltip_inlet = ["Config/MIDI data input"]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 1, 0, init_type, init_args, patch, scope, name, defs)
        self.port = 0
        self.channel = None

        extra=defs or {}
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
            MFPApp().midi_mgr.send(self.port, event)


def register():
    MFPApp().register("midi_in", MidiIn)
    MFPApp().register("midi_out", MidiOut)
