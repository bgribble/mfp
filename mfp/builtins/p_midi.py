#! /usr/bin/env python
'''
p_midi.py: builtins for MIDI I/O

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from .. import midi

class MidiIn (Processor):
	def __init__(self, init_type, init_args):
		Processor.__init__(self, 1, 1, init_type, init_args)

		self.port = 0
		self.channels = []

		midi.register(self.send)

	def trigger(self):
		event = self.inlets[0]
		if isinstance(event, dict):
			for attr, val in event.items():
				setattr(self, attr, val)
		elif isinstance(event, MethodCall):
			self.method(event, 0)
		elif isinstance(event, [ NoteEvent, MidiCCEvent, MidiMiscEvent ]):
			if event.port == self.port and (self.channels == [] or event.channel in self.channels):
				self.outlets[0] = event

class MidiOut (Processor):
	def __init__(self, init_type, init_args):
		self.port = 0

	def trigger(self):
		event = self.inlets[0]

		if isinstance(event, dict):
			for attr, val in event.items():
				setattr(self, attr, val)
		elif isinstance(event, MethodCall):
			self.method(event, 0)
		elif isinstance(event, [ NoteEvent, MidiCCEvent, MidiMiscEvent ]):
			event.port = self.port
			midi.send(event)

def register():
	MFPApp().register("midi_in~", MidiIn)
	MFPApp().register("midi_out~", MidiOut)
