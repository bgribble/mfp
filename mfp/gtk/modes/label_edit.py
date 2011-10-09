#! /usr/bin/env python2.6
'''
label_edit.py: Minor mode for editing contents of a clutter.Text label

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode 

# FIXME: need to handle motion differently if markup is enabled
class LabelEditMode (InputMode):
	def __init__(self, window, element, label, multiline=False, value=False, markup=False):
		self.manager = window.input_mgr 
		self.element = element 
		self.widget = label
		self.multiline = multiline 
		self.markup = markup
		self.text = self.widget.get_text()
		self.undo_stack  = [ self.text ] 
		self.undo_pos = -1
		self.editpos = 0

		InputMode.__init__(self, "LabelEditMode")
	
		self.default = self.insert_char

		if not self.multiline:
			self.bind("RET", self.commit_edits, "label-commit-edits")
		else:
			self.bind("C-RET", self.commit_edits, "label-commit-edits")
			self.bind("RET", lambda: self.insert_char("\n"), "insert-nl")

		self.bind("ESC", self.rollback_edits, "label-rollback-edits")
		self.bind("DEL", self.erase_forward, "label-erase-forward")
		self.bind("BS", self.erase_backward, "label-erase-backward")
		self.bind("LEFT", self.move_left, "label-move-left")
		self.bind("RIGHT", self.move_right, "label-move-right")
		self.bind("C-z", self.undo_edit, "label-undo-typing")
		self.bind("C-r", self.redo_edit, "label-redo-typing")

		self.update_label(raw=True)
		self.element.label_edit_start()

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
		self.element.label_edit_finish(self.widget)
		self.element.end_edit()
		return True 

	def rollback_edits(self):
		self.text=self.undo_stack[0]
		self.update_label(raw=False)
		self.widget.set_cursor_visible(False)
		self.element.label_edit_finish(self.widget)
		self.element.end_edit()
		return True 

	def erase_forward(self):
		if self.editpos > (len(self.text) -1):
			return 

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
			return 

		if self.undo_pos < -1:
			self.undo_stack[self.undo_pos:] = []
			self.undo_pos = -1

		self.undo_stack.append(self.text)
		self.text = self.text[:self.editpos-1] + self.text[self.editpos:]
		self.editpos = max(self.editpos - 1, 0)
		self.update_label(raw=True)
		return True 

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
			self.widget.set_text(self.text)
		else:
			self.widget.set_markup(self.text)

		return True 



					
