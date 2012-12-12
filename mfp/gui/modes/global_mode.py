#! /usr/bin/env python
'''
global_mode.py: Global input mode bindings

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode 

class GlobalMode (InputMode):
	def __init__(self, window):
		self.manager = window.input_mgr 
		self.window = window 
		InputMode.__init__(self, "Global input bindings")

		# global keybindings 
		self.bind("PGUP", self.window.layer_select_up, "Select higher layer")
		self.bind("PGDN", self.window.layer_select_down, "Select lower layer")
		self.bind('C-e', self.window.toggle_major_mode, "Toggle edit/control")
		self.bind('C-q', self.window.quit, "Quit")


