#! /usr/bin/env python
'''
autoplace.py 
Input mode to automatically select a location for the next-created GUI item 

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..patch_element import PatchElement 
from ..connection_element import ConnectionElement 
from ..input_mode import InputMode 
from mfp import log

class AutoplaceMode (InputMode):
	NONE_SPACING = 50 
	BELOW_SPACING = 25 
	ABOVE_SPACING = 50 
	CLOSE_SPACING = 10
	X_CLEAR = 50
	Y_CLEAR = 35
	X_OFF = 25 
	Y_OFF = 25 

	def __init__(self, window, callback=None, initially_below=True):
		self.window = window 
		self.callback = callback

		self.key_widget = window.selected 
		self.placement = 0

		InputMode.__init__(self, "Auto-place next element")

		self.bind("a", self.autoplace_below, "Choose next (below)")
		self.bind("A", self.autoplace_above, "Choose next (above)")
		self.bind("ESC", self.autoplace_disable, "Return to manual positioning")

		if initially_below:
			self.autoplace_below()
		else:
			self.autoplace_above()

	def _set_autoplace(self, x, y):
		self.window.show_autoplace_marker(x, y)
		if self.callback:
			self.callback(x, y)

	def autoplace_above(self):
		# if selection has changed, reset placement number 
		if self.window.selected and self.window.selected != self.key_widget:
			self.placement = 0 
			self.key_widget = self.window.selected 
	
		if self.key_widget is None:
			if len(self.window.objects):
				self.window.key_widget = self.window.objects[-1]
			else: 
				return self.autoplace_noselection()

		# there is a key widget.  Placements are above the inlets,
		# offset by SPACING 
		if self.placement == self.key_widget.num_inlets:
			self.placement = 0 

		if self.placement < self.key_widget.num_inlets:
			x, y = self.key_widget.port_center(PatchElement.PORT_IN, self.placement)
			x -= (PatchElement.porthole_border + PatchElement.porthole_width/2.0) 
			y = self.find_free_space_up(x, y - self.ABOVE_SPACING) 
		
		self._set_autoplace(x, y)	
		self.placement += 1 
		
		return True 

	def autoplace_below(self):
		# if selection has changed, reset placement number 
		if self.window.selected and self.window.selected != self.key_widget:
			self.placement = 0 
			self.key_widget = self.window.selected 
	
		if self.key_widget is None:
			if len(self.window.objects):
				self.window.key_widget = self.window.objects[-1]
			else: 
				return self.autoplace_noselection()

		# there is a key widget.  Placements are below the outlets, 
		# offset by SPACING 
		if self.placement == self.key_widget.num_outlets:
			self.placement = 0 

		if self.placement < self.key_widget.num_outlets:
			x, y = self.key_widget.port_center(PatchElement.PORT_OUT, self.placement)
			x -= (PatchElement.porthole_border + PatchElement.porthole_width/2.0) 
			y = self.find_free_space_down(x, y + self.BELOW_SPACING) 
		
		self._set_autoplace(x, y)	
		self.placement += 1 
		
		return True 

	def find_free_space_up(self, x, y):
		test_y = y 
		width, height = self.window.stage.get_size() 
		while (test_y > 0):
			clear = True
			for o in self.window.objects: 
				ow, oh = o.get_size() 
				if isinstance(o, ConnectionElement):
					continue
				elif (o.position_x > x+self.X_CLEAR 
					  or o.position_x + ow < x): 
					continue
				elif (o.position_y > test_y + self.Y_CLEAR
					  or o.position_y + oh < test_y):
					continue 
				clear = False 
			if clear:
				return test_y
			else:
				test_y -= 10
		return y


	def find_free_space_down(self, x, y):
		test_y = y 
		width, height = self.window.stage.get_size() 
		while (test_y < height - self.Y_CLEAR):
			clear = True
			overlaps = [] 
			for o in self.window.objects: 
				ow, oh = o.get_size() 
				if isinstance(o, ConnectionElement):
					continue
				elif (o.position_x > x+self.X_CLEAR 
					  or o.position_x + ow < x): 
					continue
				elif (o.position_y > test_y + self.Y_CLEAR
					  or o.position_y + oh < test_y):
					continue 
				clear = False 
			if clear:
				return test_y
			else:
				test_y += 10
		return y


	def autoplace_noselection(self):
		width, height = self.window.stage.get_size()
		spacing = self.NONE_SPACING 
		cols = int(width / spacing)
		rows = int(height / spacing)

		if self.placement > rows * cols:
			self.placement = 0 

		log.debug(self.placement, width, cols, height, rows)

		x = self.X_OFF + (self.placement % cols) * spacing
		y = self.Y_OFF + int(self.placement / cols) * spacing 

		self._set_autoplace(x, y)

		self.placement += 1 
		return True 

	def autoplace_disable(self):
		self.window.hide_autoplace_marker()
		if self.callback:
			self.callback(None, None)

	def close(self):
		self.window.hide_autoplace_marker()
		
	
