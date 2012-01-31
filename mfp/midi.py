#! /usr/bin/env python2.7
'''
midi.py: MIDI handling for MFP 

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import alsaseq
from threading import Thread
from datetime import datetime 
from . import appinfo 

class MFPMidiManager(Thread): 
	def __init__(self, inports, outports):
		self.num_inports = inports
		self.num_outports = outports
		self.start_time = None 
		self.handlers = {} 

		self.quitreq = False 	

	def register(self, callback, ports):
		for p in ports: 
			hh = self.handlers.setdefault(p, [])
			hh.append(callback)

	def start(self):
		alsaseq.client(appinfo.name, self.num_inports, self.num_outports, True)
		self.start_time = datetime.now()
		alsaseq.start()

		while not self.quitreq:
			events = alsaseq.input()
			print events 
	
	def send(self, port, data):
		pass


class ALSAFormatError (Exception):
	pass

eventmap = {
	alsaseq.SND_SEQ_EVENT_SYSTEM: MidiNoteOn,
	alsaseq.SND_SEQ_EVENT_RESULT: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_NOTE: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_NOTEON: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_NOTEOFF: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_KEYPRESS: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_CONTROLLER: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_PGMCHANGE: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_CHANPRESS: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_PITCHBEND: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_PITCHBEND: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_PITCHBEND: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_PITCHBEND: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_PITCHBEND: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_PITCHBEND: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_PITCHBEND: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_PITCHBEND: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_PITCHBEND: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_PITCHBEND: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_PITCHBEND: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_PITCHBEND: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_PITCHBEND: MidiNoteOff,
	alsaseq.SND_SEQ_EVENT_PITCHBEND: MidiNoteOff,
}

def midi_event_factory(eventdata):
	ctor = eventmap.get(eventdata[0])
	if ctor is not None:
		return ctor(*eventdata)


