#! /usr/bin/env python2.6
'''
patch_edit.py: PatchEdit major mode 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode 

class PatchEditMode (InputMode):
	def __init__(self, window):
		self.manager = window.input_mgr 
		self.window = window 

		InputMode.__init__(self, "Patch editing major mode")
		
		self.bind("C-a", self.window.add_processor, "patch-add-processor")
		self.bind("C-t", self.window.add_text, "patch-add-text")
		self.bind("C-m", self.window.add_message, "patch-add-message")
	
		

