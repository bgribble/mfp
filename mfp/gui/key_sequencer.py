#! /usr/bin/env python2.6
'''
key_sequencer.py: Collect modifiers and key/mouse clicks into Emacs-like strings

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from .key_defs import * 
from mfp import log 

def get_key_unicode(ev):
	if ev.unicode_value:
		return ord(ev.unicode_value)
	else:
		v = Clutter.keysym_to_unicode(ev.keyval)
		return v 

class KeySequencer (object):
	def __init__(self):
		self.mouse_buttons = set()
		self.mod_keys = set()
		
		self.sequences = [] 

	def pop(self):
		if len(self.sequences):
			rval = self.sequences[0]
			self.sequences[:1] = []
			return rval
		else:
			return None 

	def process(self, event):
		from gi.repository import Clutter 
	
		# KEY PRESS 
		if event.type == Clutter.EventType.KEY_PRESS: 
			code = event.keyval
			if code in MOD_ALL:
				self.mod_keys.add(code)
			else:
				self.sequences.append(self.canonicalize(event))

		# KEY RELEASE 
		elif event.type == Clutter.EventType.KEY_RELEASE:
			code = event.keyval
			if code in MOD_ALL:
				try:
					self.mod_keys.remove(code)
				except KeyError:
					pass

		# BUTTON PRESS, BUTTON RELEASE, MOUSE MOTION
		elif event.type in (Clutter.EventType.BUTTON_PRESS, Clutter.EventType.BUTTON_RELEASE, Clutter.EventType.MOTION,
					        Clutter.EventType.SCROLL):
			self.sequences.append(self.canonicalize(event))	
		
	def canonicalize(self, event):
		from gi.repository import Clutter 
		key = ''
		
		if (MOD_CTRL in self.mod_keys) or (MOD_RCTRL in self.mod_keys):
			key += 'C-'
		if (MOD_ALT in self.mod_keys) or (MOD_RALT in self.mod_keys): 
			key += 'A-'
		if (MOD_WIN in self.mod_keys) or (MOD_RWIN in self.mod_keys):
			key += 'W-'

		if event.type in (Clutter.EventType.KEY_PRESS, Clutter.EventType.KEY_RELEASE):
			ks = event.keyval
			if ks >= 256 and ((MOD_SHIFT in self.mod_keys) or (MOD_RSHIFT in self.mod_keys)):
				key = 'S-' + key 
		    	
			if ks in (KEY_TAB, KEY_SHIFTTAB):
				key += 'TAB'
			elif ks == KEY_UP:
				key += 'UP'
			elif ks == KEY_DN:
				key += 'DOWN'
			elif ks == KEY_LEFT:
				key += 'LEFT'
			elif ks == KEY_RIGHT:
				key += 'RIGHT'
			elif ks == KEY_ENTER:
				key += 'RET'
			elif ks == KEY_ESC:
				key += 'ESC'
			elif ks == KEY_DEL:
				key += 'DEL'
			elif ks == KEY_BKSP:
				key += 'BS'
			elif ks == KEY_INS:
				key += 'INS'
			elif ks == KEY_PGUP:
				key += 'PGUP'
			elif ks == KEY_PGDN:
				key += 'PGDN'
			elif ks < 256:
				kuni = get_key_unicode(event)
				if kuni < 32:
					ks = chr(event.keyval)
					if (MOD_SHIFT in self.mod_keys) or (MOD_RSHIFT in self.mod_keys):
						log.debug("SHIFT in modifiers but below 256 (%s)" % kuni)
						ks = ks.upper()
					key += ks 
				else:
					key += chr(kuni)
			else:
				log.debug("unhandled keycode", ks)
				key += "%d" % ks
			return key 

		if (MOD_SHIFT in self.mod_keys) or (MOD_RSHIFT in self.mod_keys):
			key = 'S-' + key

		if event.type in (Clutter.EventType.BUTTON_PRESS, Clutter.EventType.BUTTON_RELEASE):
			button = event.button
			clicks = event.click_count
			key += "M%d" % button

			if clicks == 2:
				key += "DOUBLE"
			elif clicks == 3:
				key += "TRIPLE"
		
			if event.type == Clutter.EventType.BUTTON_PRESS:
				key += 'DOWN'
				self.mouse_buttons.add(button)
			else:
				key += 'UP'
				self.mouse_buttons.remove(button)

		elif event.type == Clutter.EventType.MOTION:
			for b in (1,2,3):
				if b in self.mouse_buttons:
					key += 'M%d-' % b
			key += 'MOTION'

		elif event.type == Clutter.EventType.SCROLL:
			for b in (1,2,3):
				if b in self.mouse_buttons:
					key += 'M%d-' % b
			key += 'SCROLL'
			if event.direction == Clutter.ScrollDirection.DOWN:
				key += 'DOWN'
			elif event.direction == Clutter.ScrollDirection.UP:
				key += 'UP'
		return key 	



	
