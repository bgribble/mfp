#! /usr/bin/env python2.6
'''
patch_edit.py: PatchEdit major mode 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode 
from .connection import ConnectionMode

class PatchEditMode (InputMode):
	def __init__(self, window):
		self.manager = window.input_mgr 
		self.window = window 

		InputMode.__init__(self, "PatchEditMode")
		
		self.bind("C-a", self.window.add_processor, "patch-add-processor")
		self.bind("C-t", self.window.add_text, "patch-add-text")
		self.bind("C-m", self.window.add_message, "patch-add-message")
		self.bind("TAB", self.window.select_next, "patch-select-next")
		self.bind("S-TAB", self.window.select_prev, "patch-select-prev")
		self.bind("C-TAB", self.window.select_mru, "patch-select-mru")
	
		self.bind("UP", lambda: self.window.move_selected(0, -1), "patch-move-up-1")
		self.bind("DOWN", lambda: self.window.move_selected(0, 1), "patch-move-down-1")
		self.bind("LEFT", lambda: self.window.move_selected(-1, 0), "patch-move-left-1")
		self.bind("RIGHT", lambda: self.window.move_selected(1, 0), "patch-move-right-1")

		self.bind("S-UP", lambda: self.window.move_selected(0, -5), "patch-move-up-5")
		self.bind("S-DOWN", lambda: self.window.move_selected(0, 5), "patch-move-down-5")
		self.bind("S-LEFT", lambda: self.window.move_selected(-5, 0), "patch-move-left-5")
		self.bind("S-RIGHT", lambda: self.window.move_selected(5, 0), "patch-move-right-5")

		self.bind("C-UP", lambda: self.window.move_selected(0, -25), "patch-move-up-25")
		self.bind("C-DOWN", lambda: self.window.move_selected(0, 25), "patch-move-down-25")
		self.bind("C-LEFT", lambda: self.window.move_selected(-25, 0), "patch-move-left-25")
		self.bind("C-RIGHT", lambda: self.window.move_selected(25, 0), "patch-move-right-25")

		self.bind("c", self.connect_fwd, "patch-connect-fwd")
		self.bind("S-c", self.connect_rev, "patch-connect-rev")

	def connect_fwd(self):
		if self.window.selected:
			self.manager.enable_minor_mode(ConnectionMode(self.window, self.window.selected))
	
	def connect_rev(self):
		if self.window.selected:
			self.manager.enable_minor_mode(ConnectionMode(self.window, self.window.selected, 
												          connect_rev=True))
	


