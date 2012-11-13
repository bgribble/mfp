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
from ..plot_element import PlotElement
from ..slidemeter_element import FaderElement, BarMeterElement 

class PatchEditMode (InputMode):
	def __init__(self, window):
		self.manager = window.input_mgr 
		self.window = window 
		self.drag_started = False
		self.drag_start_off_x = None
		self.drag_start_off_y = None 
		self.drag_target = None 

		InputMode.__init__(self, "Edit")
		
		self.bind("p", lambda: self.window.add_element(ProcessorElement), 
			"Add processor box")
		self.bind("t", lambda: self.window.add_element(TextElement), 
			"Add text comment")
		self.bind("m", lambda: self.window.add_element(MessageElement), 
			"Add message box")
		self.bind("n", lambda: self.window.add_element(EnumElement), 
			"Add number box")
		self.bind("f", lambda: self.window.add_element(FaderElement), 
			"Add fader")
		self.bind("b", lambda: self.window.add_element(BarMeterElement), 
			"Add bar meter")
		self.bind("x", lambda: self.window.add_element(PlotElement), 
			"Add X/Y plot")
		
		self.bind("TAB", self.window.select_next, 
			"Select next element")
		self.bind("S-TAB", self.window.select_prev, 
			"Select previous element")
		self.bind("C-TAB", self.window.select_mru, 
			"Select most-recent element")
		
		self.bind("UP", lambda: self.window.move_selected(0, -1), 
			"Move element up 1 unit")
		self.bind("DOWN", lambda: self.window.move_selected(0, 1), 
			"Move element down 1 unit")
		self.bind("LEFT", lambda: self.window.move_selected(-1, 0), 
			"Move element left one unit")
		self.bind("RIGHT", lambda: self.window.move_selected(1, 0), 
			"Move element right one unit") 

		self.bind("S-UP", lambda: self.window.move_selected(0, -5), "Move element up 5")
		self.bind("S-DOWN", lambda: self.window.move_selected(0, 5), "Move element down 5")
		self.bind("S-LEFT", lambda: self.window.move_selected(-5, 0), "Move element left 5")
		self.bind("S-RIGHT", lambda: self.window.move_selected(5, 0), "Move element right 5")

		self.bind("C-UP", lambda: self.window.move_selected(0,  25), "Move element up 25")
		self.bind("C-DOWN", lambda: self.window.move_selected(0, 25), "Move element down 25")
		self.bind("C-LEFT", lambda: self.window.move_selected( 25, 0), "Move element left 25")
		self.bind("C-RIGHT", lambda: self.window.move_selected(25, 0), "Move element right 25")

		self.bind("c", self.connect_fwd, "Connect from element")
		self.bind("C", self.connect_rev, "Connect to element")

		self.bind("DEL", self.window.delete_selected, "Delete element")
		self.bind("BS", self.window.delete_selected, "Delete element")
		self.bind("RET", self.window.edit_selected, "Edit element")

		self.bind("M1DOWN", self.drag_start)
		self.bind("M1-MOTION", self.drag_selected)
		self.bind("M1UP", self.drag_end)

		self.bind('+', lambda: self.window.zoom_in(1.25), "Zoom view in")
		self.bind('=', lambda: self.window.zoom_in(1.25), "Zoom view in")
		self.bind('-', lambda: self.window.zoom_out(0.8), "Zoom view out")
		self.bind('SCROLLUP', lambda: self.window.zoom_in(1.06), "Zoom view in")
		self.bind('SCROLLDOWN', lambda: self.window.zoom_in(0.95), "Zoom view out")
		self.bind('C-0', self.window.reset_zoom, "Reset view position and zoom")

	def drag_start(self):
		if self.manager.pointer_obj is None:
			self.window.unselect_all()
		elif self.manager.pointer_obj != self.window.selected:
			self.window.select(self.manager.pointer_obj)

		self.drag_started = True
		self.drag_target = self.manager.pointer_obj

		if self.manager.pointer_obj is None: 
			px = self.manager.pointer_ev_x
			py = self.manager.pointer_ev_y
		else:
			px = self.manager.pointer_x
			py = self.manager.pointer_y

		self.drag_start_x = px
		self.drag_start_y = py
		self.drag_last_x = px
		self.drag_last_y = py 


	def drag_selected(self):
		if self.drag_started is False:
			return

		if self.drag_target is None:
			px = self.manager.pointer_ev_x
			py = self.manager.pointer_ev_y
		else:
			px = self.manager.pointer_x
			py = self.manager.pointer_y
			
		dx = px - self.drag_last_x
		dy = py - self.drag_last_y 
		
		self.drag_last_x = px
		self.drag_last_y = py 

		if self.drag_target is None:
			self.window.move_view(dx, dy)
		else:
			self.drag_target.drag(dx, dy)

	def drag_end(self):
		self.drag_started = False
		if self.drag_target:
			self.drag_target.send_params()
		self.drag_target = None 

	def connect_fwd(self):
		if self.window.selected:
			self.manager.enable_minor_mode(ConnectionMode(self.window, self.window.selected))
		return True 
	
	def connect_rev(self):
		if self.window.selected:
			self.manager.enable_minor_mode(ConnectionMode(self.window, self.window.selected, 
												          connect_rev=True))
		return True 
	


