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
from mfp.gui_slave import MFPGUI

from .key_defs import * 

class ConsoleMgr (Thread):
	def __init__ (self, banner, textview, textbuffer):
		self.quitreq = False 
		self.lock = Lock()
		self.condition = Condition(self.lock)
		self.textbuffer = textbuffer 
		self.textview = textview 

		self.linebuf = ''
		self.history_linebuf = ''
		self.history = [] 
		self.history_pos = -1 
		self.cursor_pos = 0
		self.ready = False 

		self.ps1 = '>>> '
		self.ps2 = '... '
		self.last_ps = self.ps1

		self.textview.connect('key-press-event', self.key_pressed)
		self.textview.connect('button-press-event', self.button_pressed)

		self.append(banner + '\n') 

		Thread.__init__(self)

	def button_pressed(self, *args):
		# ignore pesky mousing 
		return True 

	def key_pressed(self, widget, event):
		from gi.repository import Gdk
		
		if event.keyval == KEY_ENTER: 
			self.append("\n")
			self.linebuf = self.linebuf.strip()
			if (len(self.linebuf) 
	            and (not len(self.history) or self.linebuf != self.history[0])):
				self.history[:0] = [ self.linebuf ] 
				self.history_pos = -1 
			self.line_ready()
			return True 
		elif event.keyval == KEY_BKSP:
			if self.cursor_pos > 0:
				self.linebuf = (self.linebuf[:self.cursor_pos -1] + self.linebuf[self.cursor_pos:])
				self.cursor_pos -= 1
				self.redisplay()
			return True
		elif (event.keyval == KEY_DEL or event.string == CTRL_D):
			if self.cursor_pos < len(self.linebuf):
				self.linebuf = (self.linebuf[:self.cursor_pos] + self.linebuf[self.cursor_pos+1:])
				self.redisplay()
			return True
		elif event.keyval == KEY_UP:
			if self.history_pos >= -1 and self.history_pos < len(self.history)-1:
				if self.history_pos == -1:
					self.history_linebuf = self.linebuf 
				self.history_pos += 1 
				self.linebuf = self.history[self.history_pos]
				self.cursor_pos = len(self.linebuf)
				self.redisplay()
			return True 
		elif event.keyval == KEY_DN:
			if self.history_pos > -1 and self.history_pos < len(self.history):
				self.history_pos -= 1 
				if self.history_pos == -1:
					self.linebuf = self.history_linebuf
				else:
					self.linebuf = self.history[self.history_pos]
				self.cursor_pos = len(self.linebuf)
				self.redisplay()
			return True 
		elif event.keyval  == KEY_LEFT:
			if self.cursor_pos > 0:
				self.cursor_pos -= 1
			self.redisplay()
			return True 
		elif event.keyval  == KEY_RIGHT:
			if self.cursor_pos < len(self.linebuf):
				self.cursor_pos += 1
			self.redisplay()
			return True 
		elif event.string == CTRL_A:
			self.cursor_pos = 0
			self.redisplay()
			return True 
		elif event.string == CTRL_E:
			self.cursor_pos = len(self.linebuf)
			self.redisplay()
		elif event.string == CTRL_K:
			self.linebuf = self.linebuf[:self.cursor_pos]
			self.redisplay()
		elif len(event.string) > 0:
			if ord(event.string[0]) < 32:
				return True 
			#print event.string, event.keyval, event.get_keycode()
			self.linebuf = (self.linebuf[:self.cursor_pos] + event.string 
							+ self.linebuf[self.cursor_pos:])
			self.cursor_pos += 1
			self.redisplay()
			return True

		return False 

	def redisplay(self):
		lastline = self.textbuffer.get_line_count()
		start_iter = self.textbuffer.get_iter_at_line_offset(lastline, len(self.last_ps))
		end_iter = self.textbuffer.get_end_iter() 
		self.textbuffer.delete(start_iter, end_iter)
		end_iter = self.textbuffer.get_end_iter() 
		self.textbuffer.insert(end_iter, self.linebuf, -1)
		end_iter = self.textbuffer.get_end_iter() 
		self.textview.scroll_to_iter(end_iter, 0.2, False, 0, 0)

		cursiter = self.textbuffer.get_iter_at_line_offset(lastline, 
														   len(self.last_ps) + self.cursor_pos)
		self.textbuffer.place_cursor(cursiter)

	def line_ready(self):
		self.ready = True 
		with self.lock:
			self.condition.notify()

	def readline(self):
		'''
		Try to return a complete line, or None if one is not ready
		'''

		def try_once():
			if self.ready:
				buf = self.linebuf
				self.linebuf = ''
				self.cursor_pos = 0
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
		iterator = self.textbuffer.get_end_iter()
		self.textview.scroll_to_iter(iterator, 0.2, False, 0, 0)

	def run(self):
		time.sleep(0.1)
		continued = False 

		while not self.quitreq:
			# write the line prompt 
			if not continued: 
				self.last_ps = self.ps1 
				MFPGUI().clutter_do(lambda: self.append(self.ps1))

			else:
				self.last_ps = self.ps2
				MFPGUI().clutter_do(lambda: self.append(self.ps2))

			# wait for input, possibly quitting if needed 
			cmd = None 
			while cmd is None and not self.quitreq:
				cmd = self.readline()

			continued = self.evaluate(cmd)

	def evaluate(self, cmd):
		# returns True if a syntactically complete but partial line 
		# was entered, so we can display a continuation prompt 

		# returns False if an incorrect or complete and correct 
		# expression was entered. 
		return MFPCommand().console_eval(cmd)

	def finish(self):
		self.quitreq = True 
		try: 
			self.join()
		except:
			pass 

