#! /usr/bin/env python2.6
'''
patch_control.py: PatchControlMode major mode 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from ..input_mode import InputMode
 
class PatchControlMode (InputMode):
	def __init__(self, window):
		self.window = window 

		InputMode.__init__(self, "Patch control major mode")


