#! /usr/bin/env python2.6
'''
key_sequencer.py: Collect modifiers and key/mouse clicks into Emacs-like strings

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

MOD_SHIFT = 50
MOD_RSHIFT = 62
MOD_CTRL = 66
MOD_ALT = 64
MOD_WIN = 133
KEY_ESC = 65307 
KEY_TAB = 65289 
KEY_BKSP = 65288
KEY_PGUP = 65365
KEY_PGDN = 65366
KEY_HOME = 65360
KEY_END = 65367
KEY_INS = 65379
KEY_DEL = 65535
KEY_UP = 65362
KEY_DN = 65364
KEY_LEFT = 65361
KEY_RIGHT = 65363
KEY_ENTER = 65293 

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
		import clutter 
	
		# KEY PRESS 
		if event.type == clutter.KEY_PRESS: 
			code = event.get_key_code()
			if code in (MOD_SHIFT, MOD_CTRL, MOD_ALT, MOD_WIN):
				self.mod_keys.add(code)
			elif code == MOD_RSHIFT:
				self.mod_keys.add(MOD_SHIFT)
			else:
				self.sequences.append(self.canonicalize(event))

		# KEY RELEASE 
		elif event.type == clutter.KEY_RELEASE:
			code = event.get_key_code()
			if code in (MOD_SHIFT, MOD_CTRL, MOD_ALT, MOD_WIN):
				try:
					self.mod_keys.remove(code)
				except KeyError:
					pass
			elif code == MOD_RSHIFT:
				self.mod_keys.remove(MOD_SHIFT)

		# BUTTON PRESS, BUTTON RELEASE, MOUSE MOTION
		elif event.type in (clutter.BUTTON_PRESS, clutter.BUTTON_RELEASE, clutter.MOTION):
			self.sequences.append(self.canonicalize(event))	
		
	def canonicalize(self, event):
		import clutter 
		key = ''
		
		if MOD_CTRL in self.mod_keys:
			key += 'C-'
		if MOD_ALT in self.mod_keys: 
			key += 'A-'
		if MOD_WIN in self.mod_keys:
			key += 'W-'

		if event.type in (clutter.KEY_PRESS, clutter.KEY_RELEASE):
			ks = event.get_key_symbol()
			if ks >= 256 and MOD_SHIFT in self.mod_keys:
				key = 'S-' + key 
		    	
			if ks == KEY_TAB:
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
			elif ks < 256:
				kuni = event.get_key_unicode()
				if kuni < 32:
					ks = chr(event.get_key_symbol())
					if MOD_SHIFT in self.mod_keys:
						ks = ks.upper()
					key += ks 
				else:
					key += chr(kuni)
			else:
				key += "%d" % ks
		elif event.type in (clutter.BUTTON_PRESS, clutter.BUTTON_RELEASE):
			button = event.get_button()
			clicks = event.get_click_count()
			key += "M%d" % button

			if clicks == 2:
				key += "DOUBLE"
			elif clicks == 3:
				key += "TRIPLE"
		
			if event.type == clutter.BUTTON_PRESS:
				key += 'DOWN'
				self.mouse_buttons.add(button)
			else:
				key += 'UP'
				self.mouse_buttons.remove(button)

		elif event.type == clutter.MOTION:
			for b in (1,2,3):
				if b in self.mouse_buttons:
					key += 'M%d-' % b
			key += 'MOTION'
		
		return key 	



	
