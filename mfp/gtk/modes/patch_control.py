#! /usr/bin/env python2.6
'''
patch_control.py: PatchControlMode major mode 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from ..input_mode import InputMode
 
class PatchControlMode (InputMode):
	def __init__(self, window):
		self.manager = window.manager
		self.window = window 

		InputMode.__init__(self, "Patch control major mode")

		self.bind("TAB", self.window.select_next, "patch-select-next")
		self.bind("S-TAB", self.window.select_prev, "patch-select-prev")

