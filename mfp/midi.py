#! /usr/bin/env python2.7
'''
midi.py: MIDI handling for MFP 

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import alsaseq
from threading import Thread
from datetime import datetime 
from . import appinfo 

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


class MidiUndef (object):
	def __init__(self, seqevent=None):
		self.seqevent = seqevent

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

	def __repr__(self):
		return "<NoteOn %d %d %d>" % (self.key, self.velocity, self.channel)

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

	def __repr__(self):
		return "<NoteOff %d %d %d>" % (self.key, self.velocity, self.channel)

class MidiControl (object):
	def __init__(self, seqevent=None):
		self.seqevent = seqevent
		self.channel = None
		self.controller = None
		self.value = None 

		if self.seqevent is not None:
			self.channel = seqevent.data[0]
			self.controller = seqevent.data[1]
			self.value = seqevent.data[2]

class MFPMidiManager(Thread): 
	etypemap = {
		alsaseq.SND_SEQ_EVENT_SYSTEM: MidiUndef,
		alsaseq.SND_SEQ_EVENT_RESULT: MidiUndef,
		alsaseq.SND_SEQ_EVENT_NOTE: MidiUndef,
		alsaseq.SND_SEQ_EVENT_NOTEON: NoteOn,
		alsaseq.SND_SEQ_EVENT_NOTEOFF: NoteOff,
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
		Thread.__init__(self)

	def register(self, callback, ports=None):
		if ports is None:
			ports = [0]

		for p in ports: 
			hh = self.handlers.setdefault(p, [])
			hh.append(callback)

	def run(self):
		alsaseq.client(appinfo.name, self.num_inports, self.num_outports, True)
		self.start_time = datetime.now()
		alsaseq.start()

		while not self.quitreq:
			raw_event = alsaseq.input()
			new_event = self.create_event(raw_event)
			self.dispatch_event(new_event)

	def create_event(self, raw_event):
		ctor = self.etypemap.get(raw_event[0])
		if ctor is None:
			print "midi.py: no constructor for", raw_event
			ctor = MidiUndef
		# special case for NoteOn with velocity 0 -- it's a NoteOff,
		# treat it as such 
		elif ctor is NoteOn:
			non = ctor(SeqEvent(*raw_event))
			if non.velocity == 0:
				return NoteOff(SeqEvent(*raw_event))
		return ctor(SeqEvent(*raw_event))

	def dispatch_event(self, event):
		handlers = self.handlers.get(event.seqevent.dst[1], None)
		if handlers is None:
			return

		for h in handlers:
			h(event)

	def send(self, port, data):
		pass

