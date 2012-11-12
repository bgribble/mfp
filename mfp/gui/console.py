#! /usr/bin/env python
'''
console.py -- Python read-eval-print console for MFP  

Copyright (c) 2012 Bill Gribble <grib@billgribble.com> 
'''

from threading import Thread, Lock, Condition
import code 
import sys 
import select 
import time 
from mfp import log 
from mfp.main import MFPCommand
from .key_sequencer import KeySequencer
from .key_defs import * 

class ConsoleMgr (Thread):
	def __init__ (self, banner, textview, textbuffer):
		self.quitreq = False 
		self.lock = Lock()
		self.condition = Condition(self.lock)
		self.textbuffer = textbuffer 
		self.textview = textview 

		self.linebuf = ''
		self.editpos = -1
		self.ready = False 

		self.ps1 = '>>> '
		self.ps2 = '... '

		self.textview.connect('key-press-event', self.key_pressed)
		self.append(banner + '\n') 

		Thread.__init__(self)

	def key_pressed(self, widget, event):
		from gi.repository import Gdk
		print event, type(event), event.keyval,  event.string
		
		if event.keyval == KEY_ENTER: 
			self.append("\n")
			self.process()
		elif event.keyval == KEY_BKSP:
			self.line_edit(self.linebuf[:-1])
		elif len(event.string) > 0:
			self.linebuf += event.string
			self.append(event.string)

		return False 

	def push_chars(self, chars):
		with self.lock:
			self.linebuf += chars

	def process(self):
		self.ready = True 
		with self.lock:
			self.condition.notify()

	def resetbuffer(self):
		with self.lock:
			self.linebuf = ''
			self.ready = False 

	def readline(self):
		def try_once():
			if self.ready:
				buf = self.linebuf
				self.linebuf = ''
				self.ready = False 
				return buf
			else: 
				return None 

		with self.lock:
			buf = try_once()
			if buf is not None:
				return buf 
			self.condition.wait(0.2)
			buf = try_once()
			if buf is not None:
				return buf 

	def append(self, msg):
		iterator = self.textbuffer.get_end_iter()
		self.textbuffer.insert(iterator, msg, -1)
		self.textview.scroll_to_iter(iterator, 0, False, 0, 0)

	def run(self):
		time.sleep(0.1)
		continued = False 

		while not self.quitreq:
			# write the line prompt 
			if not continued: 
				self.append(self.ps1)
			else:
				self.append(self.ps2)

			# wait for input, possibly quitting if needed 
			cmd = None 
			while cmd is None and not self.quitreq:
				cmd = self.readline()

			continued = self.push(cmd)

	def push(self, cmd):
		return MFPCommand().console_push(cmd)

	def finish(self):
		self.quitreq = True 
		try: 
			self.join()
		except:
			pass 

