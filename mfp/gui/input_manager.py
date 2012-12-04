#! /usr/bin/env python2.6
'''
input_manager.py: Handle keyboard and mouse input and route through input modes

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from input_mode import InputMode
from key_sequencer import KeySequencer 
from mfp import log 

class InputManager (object):
	def __init__(self, window):
		self.window = window
		self.global_mode = InputMode("Global bindings")
		self.major_mode = None
		self.minor_modes = [] 
		self.keyseq = KeySequencer()
		self.event_sources = {} 
		self.root_source = None 
		self.pointer_x = None
		self.pointer_y = None 
		self.pointer_ev_x = None
		self.pointer_ev_y = None 
		self.pointer_obj = None 
		self.pointer_lastobj = None 

	def global_binding(self, key, action, helptext=''):
		self.global_mode.bind(key, action, helptext)

	def set_major_mode(self, mode):
		if isinstance(self.major_mode, InputMode):
			self.major_mode.close()
		self.major_mode = mode 
		self.window.display_bindings()

	def enable_minor_mode(self, mode):
		self.minor_modes[:0] = [mode]
		self.window.display_bindings()

	def disable_minor_mode(self, mode):
		mode.close()
		self.minor_modes.remove(mode)
		self.window.display_bindings()

	def synthesize(self, key):
		self.keyseq.sequences.append(key)

	def handle_event(self, stage, event):
		def show_on_hud(keysym, mode, handler):
			mdesc = hdesc = ""
			if mode and mode.description:
				mdesc = mode.description
			if handler and handler[1]:
				hdesc = handler[1]
			self.window.hud_write("%s: %s (%s)" % (keysym, hdesc, mdesc))
			#log.debug("[hud] %s: %s (%s)" % (keysym, handler[1], mode.description))

		from gi.repository import Clutter 
		keysym = None 
		if event.type in (Clutter.EventType.KEY_PRESS, Clutter.EventType.KEY_RELEASE, Clutter.EventType.BUTTON_PRESS,
					      Clutter.EventType.BUTTON_RELEASE, Clutter.EventType.SCROLL):
			self.keyseq.process(event)
			if len(self.keyseq.sequences):
				keysym = self.keyseq.pop()
		elif event.type == Clutter.EventType.MOTION:
			self.pointer_ev_x = event.x
			self.pointer_ev_y = event.y
			self.pointer_x, self.pointer_y = self.window.stage_pos(event.x, event.y)
			self.keyseq.process(event)
			if len(self.keyseq.sequences):
				keysym = self.keyseq.pop()
		elif event.type == Clutter.EventType.ENTER:
			self.pointer_obj = self.event_sources.get(event.source)
			if self.pointer_obj == self.pointer_lastobj:
				self.keyseq.mod_keys = set()
		elif event.type == Clutter.EventType.LEAVE:
			self.pointer_lastobj = self.pointer_obj
			self.pointer_obj = None
		else:
			return False 

		if keysym is not None:
			# check minor modes first 
			for minor in self.minor_modes:
				handler = minor.lookup(keysym)
				if handler is not None:
					handled = handler[0]()
					if handled: 
						show_on_hud(keysym, minor, handler)
						return True

			# then major mode 
			if self.major_mode is not None:
				handler = self.major_mode.lookup(keysym)
				if handler is not None: 
					handled = handler[0]()
					if handled: 
						show_on_hud(keysym, self.major_mode, handler)
						return True 

			# then global 
			handler = self.global_mode.lookup(keysym)
			if handler is not None: 
				handled = handler[0]()
				if handled:
					show_on_hud(keysym, self.global_mode, handler)
					return True 
			show_on_hud("Unhandled [%s]" % keysym, "", ("", ""))
		return False 


			

