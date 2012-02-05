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
	eventmap = {
		alsaseq.SND_SEQ_EVENT_SYSTEM: MidiUndef,
		alsaseq.SND_SEQ_EVENT_RESULT: MidiUndef,
		alsaseq.SND_SEQ_EVENT_NOTE: MidiNote,
		alsaseq.SND_SEQ_EVENT_NOTEON: MidiNote,
		alsaseq.SND_SEQ_EVENT_NOTEOFF: MidiNote,
		alsaseq.SND_SEQ_EVENT_KEYPRESS: MidiControl,
		alsaseq.SND_SEQ_EVENT_CONTROLLER: MidiControl,
		alsaseq.SND_SEQ_EVENT_PGMCHANGE: MidiControl,
		alsaseq.SND_SEQ_EVENT_CHANPRESS: MidiControl,
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
			for e in events:
				new_event = self.create_event(e)
				print new_event
				self.dispatch_event(new_event)

	def create_event(self, raw_event):
		etype, eflags, tag, queue, timestamp, src, dst, data = raw_event
		ctor = self.etypemap.get(etype)
		return ctor(*raw_event)

	def dispatch_event(self, event):
		handlers = self.handlers.get(event.src, [])
		for h in handlers:
			h(event)

	def send(self, port, data):
		pass


class MidiUndef (object):
	def __init__(self, *values):
		self.etype = values[0]
		self.args = values[1:]


