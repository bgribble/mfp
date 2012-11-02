#! /usr/bin/env python2.6
'''
input_manager.py: Handle keyboard and mouse input and route through input modes

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from input_mode import InputMode
from key_sequencer import KeySequencer 

class InputManager (object):
	def __init__(self):
		self.global_mode = InputMode("Global bindings")
		self.major_mode = None
		self.minor_modes = [] 
		self.keyseq = KeySequencer()
		self.event_sources = {} 
		self.root_source = None 
		self.pointer_x = None
		self.pointer_y = None 
		self.pointer_obj = None 
		self.pointer_lastobj = None 

	def global_binding(self, key, action, helptext=''):
		self.global_mode.bind(key, action, helptext)

	def set_major_mode(self, mode):
		if isinstance(self.major_mode, InputMode):
			self.major_mode.close()
		self.major_mode = mode 

	def enable_minor_mode(self, mode):
		self.minor_modes[:0] = [mode]

	def disable_minor_mode(self, mode):
		mode.close()
		self.minor_modes.remove(mode)

	def handle_event(self, stage, event):
		from gi.repository import Clutter as clutter 
		keysym = None 
		if event.type in (clutter.EventType.KEY_PRESS, clutter.EventType.KEY_RELEASE, clutter.EventType.BUTTON_PRESS,
					      clutter.EventType.BUTTON_RELEASE, clutter.EventType.SCROLL):
			self.keyseq.process(event)
			if len(self.keyseq.sequences):
				keysym = self.keyseq.pop()
		elif event.type == clutter.EventType.MOTION:
			self.pointer_x = event.x
			self.pointer_y = event.y
			self.keyseq.process(event)
			if len(self.keyseq.sequences):
				keysym = self.keyseq.pop()
		elif event.type == clutter.EventType.ENTER:
			self.pointer_obj = self.event_sources.get(event.source)
			if self.pointer_obj == self.pointer_lastobj:
				self.keyseq.mod_keys = set()
		elif event.type == clutter.EventType.LEAVE:
			self.pointer_lastobj = self.pointer_obj
			self.pointer_obj = None
		else:
			return False 

		if keysym is not None:
			# check minor modes first 
			for minor in self.minor_modes:
				handler = minor.lookup(keysym)
				if handler is not None:
					# print keysym, minor.description, ':', handler[1]
					handled = handler[0]()
					if handled: 
						return True

			# then major mode 
			if self.major_mode is not None:
				handler = self.major_mode.lookup(keysym)
				if handler is not None: 
					print keysym, self.major_mode.description, ':', handler[1]
					handled = handler[0]()
					if handled: 
						return True 

			# then global 
			handler = self.global_mode.lookup(keysym)
			if handler is not None: 
				print keysym, self.global_mode.description, ':', handler[1]
				handled = handler[0]()
				if handled:
					return True 

		return False 


			

