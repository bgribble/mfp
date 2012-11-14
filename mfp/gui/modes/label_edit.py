#! /usr/bin/env python2.6
'''
label_edit.py: Minor mode for editing contents of a clutter.Text label

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode 
from mfp import log 

class LabelEditMode (InputMode):
	def __init__(self, window, element, label, multiline=False, markup=False):
		self.manager = window.input_mgr 
		self.element = element 
		self.widget = label
		self.multiline = multiline 
		self.markup = markup
		self.text = self.widget.get_text()

		self.undo_stack  = [ self.text ] 
		self.undo_pos = -1
		self.editpos = 0

		InputMode.__init__(self, "Edit text")
	

		if not self.multiline:
			self.bind("RET", self.commit_edits, "Accept edits")
		else:
			self.bind("C-RET", self.commit_edits, "Accept edits")
			self.bind("RET", lambda: self.insert_char("\n"), "Insert newline")

		self.bind("ESC", self.rollback_edits, "Discard edits")
		self.bind("DEL", self.erase_forward, "Delete forward")
		self.bind("C-d", self.erase_forward, "Delete forward")

		self.bind("BS", self.erase_backward, "Delete backward")
		self.bind("LEFT", self.move_left, "Move cursor left")
		self.bind("RIGHT", self.move_right, "Move cursor right")
		self.bind("C-e", self.move_to_end, "Move cursor to end")
		self.bind("C-a", self.move_to_start, "Move cursor to start")
		self.bind("C-z", self.undo_edit, "Undo typing")
		self.bind("C-r", self.redo_edit, "Redo typing")

		# default binding 
		self.bind(None, self.insert_char, "Insert text")

		inittxt = self.element.label_edit_start()
		if inittxt: 
			self.text = inittxt

		self.update_label(raw=True)

	def insert_char(self, keysym):
		if len(keysym) > 1:
			return False 

		if self.undo_pos < -1:
			self.undo_stack[self.undo_pos:] = []
			self.undo_pos = -1

		self.undo_stack.append(self.text)
		self.text = self.text[:self.editpos] + keysym + self.text[self.editpos:]
		self.editpos += 1
		self.update_label(raw=True)
		return True 

	def commit_edits(self):
		self.widget.set_cursor_visible(False)
		self.update_label(raw=False)
		self.element.label_edit_finish(self.widget, self.text)
		self.element.end_edit()
		return True 

	def rollback_edits(self):
		self.text=self.undo_stack[0]
		self.update_label(raw=False)
		self.widget.set_cursor_visible(False)
		self.element.label_edit_finish(self.widget, None, aborted=True)
		self.element.end_edit()
		return True 

	def erase_forward(self):
		if self.editpos > (len(self.text) -1):
			return True 

		if self.undo_pos < -1:
			self.undo_stack[self.undo_pos:] = []
			self.undo_pos = -1
		self.undo_stack.append(self.text)
		self.text = self.text[:self.editpos] + self.text[self.editpos+1:]
		self.update_label(raw=True)
		return True 

	def erase_backward(self):
		if self.editpos <= 0:
			self.editpos = 0
			return True

		if self.undo_pos < -1:
			self.undo_stack[self.undo_pos:] = []
			self.undo_pos = -1

		self.undo_stack.append(self.text)
		self.text = self.text[:self.editpos-1] + self.text[self.editpos:]
		self.editpos = max(self.editpos - 1, 0)
		self.update_label(raw=True)
		return True 

	def move_to_start(self):
		self.editpos = 0
		self.update_label(raw=True)

	def move_to_end(self):
		self.editpos = len(self.text)
		self.update_label(raw=True)

	def move_left(self):
		self.editpos = max(self.editpos-1, 0)
		self.update_label(raw=True)
		return True 

	def move_right(self):
		self.editpos = min(self.editpos+1, len(self.text))
		self.update_label(raw=True)
		return True 

	def undo_edit(self):
		if self.undo_pos > (-len(self.undo_stack)):
			self.text = self.undo_stack[self.undo_pos] 
			self.undo_pos = max(-len(self.undo_stack), self.undo_pos - 1)
			self.update_label(raw=True)

		return True 

	def redo_edit(self):
		if self.undo_pos < -1:
			self.undo_pos += 1
			self.text = self.undo_stack[self.undo_pos] 
			self.update_label(raw=True)
		return True 

	def update_label(self, raw=True):
		if raw or self.markup is False:
			self.widget.set_use_markup = False 
			self.widget.set_text(self.text)
		else:
			self.widget.set_markup(self.text)

		return True 



					
