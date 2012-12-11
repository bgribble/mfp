#! /usr/bin/env python
'''
patch_layer.py
A layer in the patch window 
'''

from ..utils import extends 
from gi.repository import Clutter
from mfp import log 
from .patch_window import PatchWindow 
from ..main import MFPCommand 

class PatchLayer(object):
	def __init__(self, stage, patch, name, scope="__patch__"):
		self.stage = stage
		self.patch = patch 
		self.name = name 
		self.scope = scope

		self.group = Clutter.Group() 
		self.group.set_property("opacity", 0)
		self.stage.group.add_actor(self.group)

	def show(self): 
		self.group.set_property("opacity", 255) 

	def hide(self):
		self.group.set_property("opacity", 0)

@extends(PatchWindow)
def layer_select_cb(self, selection):
	from .patch_info import PatchInfo
	model, iter = selection.get_selected()
	if iter is None:
		return 

	sel_obj = self.layer_store.get_value(iter, 0)
	if isinstance(sel_obj, PatchInfo):
		layer = sel_obj.layers[0]
	elif isinstance(sel_obj, PatchLayer):
		layer = sel_obj

	if layer != self.selected_layer:
		self.layer_select(layer, do_update=False)

@extends(PatchWindow)
def layer_name_edited_cb(self, renderer, path, new_value):
	iter = self.layer_store.get_iter_from_string(path)
	layer = self.layer_store.get_value(iter, 0)
	if isinstance(layer, PatchLayer):
		layer.name = new_value
		self.selected_patch.send_params()
		for obj in self.objects: 
			if obj.layer == layer: 
				obj.send_params()
		self.layer_store_update()
	return True 

@extends(PatchWindow)
def layer_scope_edited_cb(self, renderer, path, new_value):
	iter = self.layer_store.get_iter_from_string(path)
	layer = self.layer_store.get_value(iter, 0)
	if isinstance(layer, PatchLayer):
		p = self.selected_patch
		layer.scope = new_value
		if not p.has_scope(new_value):
			MFPCommand().add_scope(new_value)
			
		self.selected_patch.send_params()
		for obj in self.objects: 
			if obj.layer == layer: 
				MFPCommand().set_scope(obj.obj_id, new_value)

		self.layer_store_update()
		self.object_store_update()
	return True 

@extends(PatchWindow)
def layer_select_up(self):
	p = self.selected_patch
	l = p.layers.index(self.selected_layer) 
	self.layer_select(p.layers[l - 1])

@extends(PatchWindow)
def layer_select_down(self):
	p = self.selected_patch
	l = p.layers.index(self.selected_layer) 
	self.layer_select(p.layers[(l + 1) % len(p.layers)])

@extends(PatchWindow)
def layer_select(self, layer, do_update=True):
	if self.selected_layer is not None:
		self.selected_layer.hide()
	self.selected_layer = layer
	self.selected_layer.show()
	sname = self.selected_layer.scope
	if sname == "__patch__":
		sname = "Patch"

	self.hud_write("Layer: <b>%s</b> (lexical scope '%s')" % (self.selected_layer.name, sname))
	if do_update:
		self.layer_selection_update()

@extends(PatchWindow)
def layer_new(self):
	l = PatchLayer(self, self.selected_patch, "Layer %d" % len(self.selected_patch.layers))
	self.selected_patch.layers.append(l)
	self.selected_patch.send_params()
	self.layer_store_update()
	self.layer_select(l)
	return True 

@extends(PatchWindow)
def layer_new_scope(self):
	l = PatchLayer(self, self.selected_patch, "Layer %d" % len(self.selected_patch.layers))
	l.scope = l.name.replace(" ", "_").lower()
	MFPCommand().add_scope(l.scope)

	self.selected_patch.layers.append(l)
	self.selected_patch.send_params()
	self.layer_store_update()
	self.layer_select(l)
	return True 

@extends(PatchWindow)
def layer_selection_update(self):
	match = [ None ] 
	def chkfunc(model, path, iter, data):
		if self.layer_store.get_value(iter, 0) == self.selected_layer:
			spath = self.layer_store.get_path(iter)
			match[:] = [ spath ]
			return True
		return False 

	if self.selected_layer is None: 
		# always should be a leyer selected, this could mean we are 
		# at startup
		if len(self.selected_patch.layers):
			self.layer_select(self.selected_patch.layers[0])
		else:
			log.debug("PROBLEM: no selected layer, this will mean trouble")
		return

	model, iter = self.layer_view.get_selection().get_selected()
	if iter is None or self.layer_store.get_value(iter, 0) != self.selected_layer:
		self.layer_store.foreach(chkfunc, None)
		if match[0] is not None: 
			spath = match[0]
			if spath is not None:
				self.layer_view.get_selection().select_path(spath)

@extends(PatchWindow)
def layer_store_update(self):
	self.layer_store.clear()
	for p in self.patches: 
		piter = self.layer_store.append(None)
		self.layer_store.set_value(piter, 0, p)
		self.layer_store.set_value(piter, 1, p.obj_name or "Default Patch")
		self.layer_store.set_value(piter, 2, "Global") 

		for l in p.layers:
			liter = self.layer_store.append(piter)
			self.layer_store.set_value(liter, 0, l)
			self.layer_store.set_value(liter, 1, l.name)
			sname = l.scope
			if not sname or sname == "__patch__":
				sname = "__patch__"
			self.layer_store.set_value(liter, 2, sname)
	self.layer_view.expand_all()



