#! /usr/bin/env python2.6
'''
patch_control.py: PatchControl major mode 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from ..input_mode import InputMode
 
class PatchControlMode (InputMode):
	def __init__(self, window):
		self.manager = window.input_mgr
		self.window = window 

		self.drag_started = True
		self.drag_start_x = self.manager.pointer_x
		self.drag_start_y = self.manager.pointer_y
		self.drag_last_x = self.manager.pointer_x
		self.drag_last_y = self.manager.pointer_y

		InputMode.__init__(self, "PatchControlMode")

		self.bind("TAB", self.window.select_next, "patch-select-next")
		self.bind("S-TAB", self.window.select_prev, "patch-select-prev")
		self.bind("C-TAB", self.window.select_mru, "patch-select-mru")

		self.bind("M1DOWN", self.drag_start, "patch-drag-start")
		self.bind("M1-MOTION", self.drag_selected, "patch-drag-selected")
		self.bind("M1UP", self.drag_end, "patch-drag-end")

		self.bind('C-0', self.window.reset_zoom, "patch-reset-zoom")
		self.bind('+', lambda: self.window.zoom_in(1.25), "patch-zoom-in")
		self.bind('=', lambda: self.window.zoom_in(1.25), "patch-zoom-in")
		self.bind('-', lambda: self.window.zoom_out(0.8), "patch-zoom-out")
		self.bind('SCROLLUP', lambda: self.window.zoom_in(1.06), "patch-zoom-in-tiny")
		self.bind('SCROLLDOWN', lambda: self.window.zoom_in(0.95), "patch-zoom-out-tiny")

	def drag_start(self):
		self.drag_started = True
		self.drag_start_x = self.manager.pointer_x
		self.drag_start_y = self.manager.pointer_y
		self.drag_last_x = self.manager.pointer_x
		self.drag_last_y = self.manager.pointer_y

	def drag_selected(self):
		if self.drag_started is False:
			return

		dx = self.manager.pointer_x - self.drag_last_x
		dy = self.manager.pointer_y - self.drag_last_y 
		
		self.drag_last_x = self.manager.pointer_x
		self.drag_last_y = self.manager.pointer_y 

		if self.manager.pointer_obj is None:
			self.window.move_view(dx, dy)

	def drag_end(self):
		self.drag_started = False

