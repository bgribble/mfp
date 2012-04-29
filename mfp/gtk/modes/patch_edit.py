#! /usr/bin/env python2.6
'''
patch_edit.py: PatchEdit major mode 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode 
from .connection import ConnectionMode

from ..text_element import TextElement
from ..processor_element import ProcessorElement
from ..connection_element import ConnectionElement 
from ..message_element import MessageElement
from ..enum_element import EnumElement
from ..chart_element import ChartElement

class PatchEditMode (InputMode):
	def __init__(self, window):
		self.manager = window.input_mgr 
		self.window = window 
		self.drag_started = False
		self.drag_start_off_x = None
		self.drag_start_off_y = None 

		InputMode.__init__(self, "PatchEditMode")
		
		self.bind("a", lambda: self.window.add_element(ProcessorElement), "patch-add-processor")
		self.bind("t", lambda: self.window.add_element(TextElement), "patch-add-text")
		self.bind("m", lambda: self.window.add_element(MessageElement), "patch-add-message")
		self.bind("n", lambda: self.window.add_element(EnumElement), "patch-add-enum")
		self.bind("s", lambda: self.window.add_element(ChartElement), "patch-add-scatter")
		self.bind("TAB", self.window.select_next, "patch-select-next")
		self.bind("S-TAB", self.window.select_prev, "patch-select-prev")
		self.bind("C-TAB", self.window.select_mru, "patch-select-mru")
		self.bind("RET", self.window.edit_selected, "patch-edit-selected")	
		
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
		self.bind("C", self.connect_rev, "patch-connect-rev")

		self.bind("DEL", self.window.delete_selected, "patch-delete-selected")
		self.bind("BS", self.window.delete_selected, "patch-delete-selected")

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
		if self.manager.pointer_obj is None:
			self.window.unselect_all()
		elif self.manager.pointer_obj != self.window.selected:
			self.window.select(self.manager.pointer_obj)

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
		elif self.window.selected and self.manager.pointer_obj == self.window.selected:
			self.window.selected.drag(dx, dy)

	def drag_end(self):
		self.drag_started = False
		if self.window.selected:
			self.window.selected.send_params()

	def connect_fwd(self):
		if self.window.selected:
			self.manager.enable_minor_mode(ConnectionMode(self.window, self.window.selected))
		return True 
	
	def connect_rev(self):
		if self.window.selected:
			self.manager.enable_minor_mode(ConnectionMode(self.window, self.window.selected, 
												          connect_rev=True))
		return True 
	


