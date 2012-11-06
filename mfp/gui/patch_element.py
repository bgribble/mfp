#! /usr/bin/env python
'''
patch_element.py
A patch element is the parent of all GUI entities backed by MFP objects 

Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter as clutter
from mfp import MFPGUI 
from mfp import log 

class PatchElement (clutter.Group):
	'''
	Parent class of elements represented in the patch window 
	'''
	PORT_IN = 0
	PORT_OUT = 1
	porthole_width = 8
	porthole_height = 4
	porthole_border = 1
	porthole_minspace = 10

	def __init__(self, window, x, y):
		# MFP object and UI descriptors 
		self.obj_id = None
		self.obj_type = None
		self.obj_args = None
		self.num_inlets = 0
		self.num_outlets = 0
		self.dsp_inlets = []
		self.dsp_outlets = []
		self.connections_out = [] 
		self.connections_in = [] 

		# Clutter objects 
		self.stage = window
		self.port_elements = {}

		# UI state 
		self.position_x = x
		self.position_y = y
		self.drag_x = None
		self.drag_y = None
		self.selected = False 
		self.update_required = False
		self.edit_mode = None
		self.control_mode = None

		# create placeholder group and add to stage 
		clutter.Group.__init__(self)
		self.stage.register(self)

	def drag_start(self, x, y):
		self.drag_x = x - self.position_x
		self.drag_y = y - self.position_y

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		self.set_position(x, y)

	def drag(self, dx, dy):
		self.move(self.position_x + dx, self.position_y + dy)

	def delete(self):
		self.stage.unregister(self)
		if self.obj_id is not None:
			MFPGUI().mfp.delete(self.obj_id)
			self.obj_id = None

	def create(self, obj_type, init_args):
		objinfo = MFPGUI().mfp.create(obj_type, init_args)
		self.obj_id = objinfo.get('obj_id')
		self.num_inlets = objinfo.get("num_inlets")
		self.num_outlets = objinfo.get("num_outlets")
		self.dsp_inlets = objinfo.get("dsp_inlets")
		self.dsp_outlets = objinfo.get("dsp_outlets")

		if self.obj_id is not None:
			MFPGUI().remember(self)
		return self.obj_id
			
	def send_params(self, **extras):
		prms = dict(position_x=self.position_x, position_y=self.position_y, 
					update_required=self.update_required, element_type=self.element_type,
					num_inlets=self.num_inlets, num_outlets=self.num_outlets, 
					dsp_inlets=self.dsp_inlets, dsp_outlets=self.dsp_outlets)
		for k, v in extras.items():
			prms[k] = v
		if self.obj_id is not None:
			MFPGUI().mfp.set_params(self.obj_id, prms)

	def get_params(self):
		return MFPGUI().mfp.get_params(self.obj_id)

	def port_center(self, port_dir, port_num):
		ppos = self.port_position(port_dir, port_num)
		return (self.position_x + ppos[0] + 0.5*self.porthole_width, 
		        self.position_y + ppos[1] + 0.5*self.porthole_height)

	def port_position(self, port_dir, port_num):
		w = self.get_width()
		h = self.get_height()

		if port_dir == PatchElement.PORT_IN:
			if self.num_inlets < 2:
				spc = 0
			else:
				spc = max(self.porthole_minspace, 
						  (w-self.porthole_width-2.0*self.porthole_border) / (self.num_inlets-1.0))
			return (self.porthole_border + spc*port_num, 0)

		elif port_dir == PatchElement.PORT_OUT:
			if self.num_outlets < 2:
				spc = 0
			else:
				spc = max(self.porthole_minspace, 
						  (w-self.porthole_width-2.0*self.porthole_border) / (self.num_outlets-1.0))
			return (self.porthole_border + spc*port_num, h-2.0-self.porthole_height)

	def draw_ports(self):
		log.debug("draw_ports:", self)

		def confport(pid, px, py):
			pobj = self.port_elements.get(pid)
			if pobj is None:
				pobj = clutter.Rectangle()
				pobj.set_color(self.stage.color_unselected)
				pobj.set_size(self.porthole_width, self.porthole_height)
				pobj.set_reactive(False)
				self.add_actor(pobj)
				self.port_elements[pid] = pobj
			pobj.set_position(px, py)

		for i in range(self.num_inlets):
			x, y = self.port_position(PatchElement.PORT_IN, i)
			pid = (PatchElement.PORT_IN, i)
			confport(pid, x, y)

		for i in range(self.num_outlets):
			x, y = self.port_position(PatchElement.PORT_OUT, i)
			pid = (PatchElement.PORT_OUT, i)
			confport(pid, x, y)


	def configure(self, params):
		self.num_inlets = params.get("num_inlets")
		self.num_outlets = params.get("num_outlets")
		self.dsp_inlets = params.get("dsp_inlets")
		self.dsp_outlets = params.get("dsp_outlets")
		self.draw_ports()

	def make_edit_mode(self):
		return None

	def make_control_mode(self):
		return None

	def begin_edit(self):
		if not self.edit_mode:
			self.edit_mode = self.make_edit_mode()

		if self.edit_mode:
			self.stage.input_mgr.enable_minor_mode(self.edit_mode)

	def end_edit(self):
		if self.edit_mode:
			self.stage.input_mgr.disable_minor_mode(self.edit_mode)
			self.edit_mode = None

	def begin_control(self):
		if not self.control_mode:
			self.control_mode = self.make_control_mode()

		if self.control_mode:
			self.stage.input_mgr.enable_minor_mode(self.control_mode)
		
	def end_control(self):
		if self.control_mode:
			self.stage.input_mgr.disable_minor_mode(self.control_mode)
			self.control_mode = None

