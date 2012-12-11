#! /usr/bin/env python
'''
patch_funcs.py
Helper methods for patch window input modes 

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''
from ..utils import extends 
from .patch_window import PatchWindow 
from .connection_element import ConnectionElement
from .modes.select_mru import SelectMRUMode 

@extends(PatchWindow)
def select(self, obj):
	if self.selected is not obj and self.selected is not None:
		self.unselect(self.selected)
	obj.select()
	self.selected = obj
	
	obj.begin_control()

	# FIXME hook
	SelectMRUMode.touch(obj) 

	self.object_selection_update()
	return True 

@extends(PatchWindow)
def unselect(self, obj):
	if self.selected is obj and obj is not None:
		obj.end_control()
		obj.unselect()
		self.selected = None
		self.object_selection_update()
	return True 

@extends(PatchWindow)
def unselect_all(self):
	if self.selected:
		self.selected.end_control()
		self.selected.unselect()
		self.selected = None
		self.object_selection_update()
	return True 

@extends(PatchWindow)
def select_next(self):
	if len(self.objects) == 0:
		return False 

	selectable = [ o for o in self.objects if not isinstance(o, ConnectionElement)]
	if self.selected is None and len(selectable) > 0:
		self.select(selectable[0])
		return True 
	else:
		cur_ind = selectable.index(self.selected)
		self.select(selectable[(cur_ind+1) % len(selectable)])
		return True 

@extends(PatchWindow)
def select_prev(self):
	if len(self.objects) == 0:
		return False 

	selectable = [ o for o in self.objects if not isinstance(o, ConnectionElement)]
	if self.selected is None and len(selectable) > 0:
		self.select(selectable[-1])
		return True 
	else:
		cur_ind = selectable.index(self.selected) 
		self.select(selectable[cur_ind-1])
		return True 

@extends(PatchWindow)
def select_mru(self):
	self.input_mgr.enable_minor_mode(SelectMRUMode(self))
	return True 

@extends(PatchWindow)
def move_selected(self, dx, dy):
	if self.selected is None or isinstance(self.selected, ConnectionElement):
		return

	self.selected.move(max(0, self.selected.position_x + dx*self.zoom),
					   max(0, self.selected.position_y + dy*self.zoom))
	if self.selected.obj_id is not None:
		self.selected.send_params()
	return True 

@extends(PatchWindow)
def delete_selected(self):
	if self.selected is None:
		return
	o = self.selected
	o.delete()
	return True 

@extends(PatchWindow)
def edit_selected(self):
	if self.selected is None:
		return True
	self.selected.begin_edit()
	return True

@extends(PatchWindow)
def rezoom(self):
	w, h = self.group.get_size()
	self.group.set_scale_full(self.zoom, self.zoom, w/2.0, h/2.0)
	self.group.set_position(self.view_x, self.view_y)

@extends(PatchWindow)
def reset_zoom(self):
	self.zoom = 1.0
	self.view_x = 0
	self.view_y = 0
	self.rezoom()
	return True 

@extends(PatchWindow)
def zoom_out(self, ratio):
	if self.zoom >= 0.1:
		self.zoom *= ratio
		self.rezoom()
	return True 
	
@extends(PatchWindow)
def zoom_in(self, ratio):
	if self.zoom < 20:
		self.zoom *= ratio
		self.rezoom()
	return True 

@extends(PatchWindow)
def move_view(self, dx, dy):
	self.view_x += dx
	self.view_y += dy
	self.rezoom()
	return True 


