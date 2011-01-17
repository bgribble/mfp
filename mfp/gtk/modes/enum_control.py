#! /usr/bin/env python2.6
'''
enum_control.py: EnumControl major mode 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode
 
class EnumControlMode (InputMode):
	def __init__(self, window, element):
		self.manager = window.input_mgr
		self.window = window 
		self.enum = element

		self.drag_started = True
		self.drag_start_x = self.manager.pointer_x
		self.drag_start_y = self.manager.pointer_y
		self.drag_last_x = self.manager.pointer_x
		self.drag_last_y = self.manager.pointer_y

		InputMode.__init__(self, "EnumControl")

		self.bind("M1DOWN", self.drag_start, "patch-drag-start")
		self.bind("M1-MOTION", lambda: self.drag_selected(0.5), "patch-drag-selected-1")
		self.bind("S-M1-MOTION", lambda: self.drag_selected(5), "patch-drag-selected-1")
		self.bind("C-M1-MOTION", lambda: self.drag_selected(50), "patch-drag-selected-1")
		self.bind("M1UP", self.drag_end, "patch-drag-end")

	def drag_start(self):
		if self.manager.pointer_obj == self.enum:
			if self.manager.pointer_obj != self.window.selected:
				self.window.select(self.manager.pointer_obj)

			self.drag_started = True
			self.drag_start_x = self.manager.pointer_x
			self.drag_start_y = self.manager.pointer_y
			self.drag_last_x = self.manager.pointer_x
			self.drag_last_y = self.manager.pointer_y
			return True
		else:
			return False

	def drag_selected(self, delta=1.0):
		if self.drag_started is False:
			return False

		dx = self.manager.pointer_x - self.drag_last_x
		dy = self.manager.pointer_y - self.drag_last_y 
		
		self.drag_last_x = self.manager.pointer_x
		self.drag_last_y = self.manager.pointer_y 

		self.enum.update_value(self.enum.value - delta*dy)
		return True

	def drag_end(self):
		if self.drag_started:
			self.drag_started = False
			return True
		else:
			return False

