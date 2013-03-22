#! /usr/bin/env python
'''
p_midi.py: builtins for MIDI I/O

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from .. import midi
from ..processor import Processor
from ..main import MFPApp
from ..method import MethodCall
from ..midi import NoteOn, NoteOff, NotePress, MidiCC, MidiPgmChange, MidiUndef


class MidiIn (Processor):
    doc_tooltip_obj = "Receive MIDI events from ALSA sequencer" 
    doc_tooltip_inlet = ["Config/MIDI passthru input" ]
    doc_tooltip_outlet = ["MIDI event output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

        self.port = 0
        self.channels = []

        MFPApp().midi_mgr.register(self.send)

    def trigger(self):
        event = self.inlets[0]
        if isinstance(event, dict):
            for attr, val in event.items():
                setattr(self, attr, val)
        elif isinstance(event, MethodCall):
            self.method(event, 0)
        elif isinstance(event, (NoteOn, NoteOff, NotePress, MidiPgmChange, MidiCC, MidiUndef)):
            if event.seqevent and event.seqevent.dst and event.seqevent.dst[1] != self.port:
                pass
            elif (self.channels == []) or (event.channel in self.channels) or event.channel == -1:
                self.outlets[0] = event


class MidiOut (Processor):
    doc_tooltip_obj = "Send MIDI events to ALSA sequencer" 
    doc_tooltip_inlet = ["Config/MIDI data input"]
    
    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 0, init_type, init_args, patch, scope, name)
        self.port = 0
        self.channel = None 

    def trigger(self):
        event = self.inlets[0]

        if isinstance(event, dict):
            for attr, val in event.items():
                setattr(self, attr, val)
        elif isinstance(event, MethodCall):
            self.method(event, 0)
        elif isinstance(event, [NoteEvent, MidiCCEvent, MidiMiscEvent]):
            event.port = self.port
            if self.channel is not None:
                event.channel = self.channel 
            midi.send(event)


def register():
    MFPApp().register("midi_in", MidiIn)
    MFPApp().register("midi_out", MidiOut)
