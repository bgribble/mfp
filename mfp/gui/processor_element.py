#! /usr/bin/env python
'''
processor_element.py
A patch element corresponding to a signal or control processor 
'''

from gi.repository import Clutter as clutter 
import cairo
import math 
from patch_element import PatchElement
from mfp import MFPGUI
from mfp import log 
from input_mode import InputMode
from .modes.label_edit import LabelEditMode

class ProcessorElement (PatchElement):
	display_type = "processor"
	proc_type = None 

	# constants 
	label_off_x = 3
	label_off_y = 0 

	def __init__(self, window, x, y, params={}):
		PatchElement.__init__(self, window, x, y)
		
		# display elements 
		self.texture = None
		self.label = None
		self.label_text = None 

		# create display 
		self.create_display()
		self.set_size(35, 25)
		self.move(x, y)

		self.obj_state = self.OBJ_HALFCREATED

		self.update()

	def create_display(self):
		# box 
		self.texture = clutter.CairoTexture.new(35, 25)
		self.texture.connect("draw", self.draw_cb)

		# label
		self.label = clutter.Text()
		self.label.set_position(self.label_off_x, self.label_off_y)
		self.label.set_color(self.stage.color_unselected) 
		self.label.connect('text-changed', self.label_changed_cb)
		self.label.set_reactive(False)

		self.add_actor(self.texture)
		self.add_actor(self.label)
		self.set_reactive(True)

	def update(self):
		# FIXME not-created style (dashed lines?)
		self.draw_ports()
		self.texture.invalidate()

	def draw_cb(self, texture, ct): 
		w = self.texture.get_property('surface_width')-1
		h = self.texture.get_property('surface_height')-1
		self.texture.clear()
		if self.selected: 
			color = self.stage.color_selected
		else:
			color = self.stage.color_unselected
		
		if self.obj_state == self.OBJ_COMPLETE:
			ct.set_dash([])
		else:
			ct.set_dash([8, 4])

		ct.set_line_width(2.0)
		ct.set_antialias(cairo.ANTIALIAS_NONE)
		ct.set_source_rgba(color.red, color.green, color.blue, 1.0)
		ct.translate(0.5, 0.5)
		ct.move_to(1, 1)
		ct.line_to(1, h)
		ct.line_to(w, h)
		ct.line_to(w, 1)
		ct.line_to(1, 1)
		ct.close_path()
		ct.stroke()

	def get_label(self):
		return self.label

	def label_edit_start(self):
		self.obj_state = self.OBJ_HALFCREATED

	def label_edit_finish(self, widget, aborted=False):
		t = self.label.get_text()

		if t != self.label_text:
			self.obj_id = None 
			parts = t.split(' ', 1)
			self.obj_type = parts[0]
			if len(parts) > 1:
				self.obj_args = parts[1]

			log.debug("ProcessorElement: processor=%s, args=%s" % (self.obj_type, self.obj_args))
			self.create(self.obj_type, self.obj_args)

			# obj_args may get forcibly changed on create
			if self.obj_args and (len(parts) < 2 or self.obj_args != parts[1]):
				self.label.set_text(self.obj_type + ' ' + self.obj_args)

		if self.obj_id is not None:
			self.obj_state = self.OBJ_COMPLETE
			self.send_params()
			self.draw_ports()

		self.update()

	def label_changed_cb(self, *args):
		'''called by clutter when label.set_text or editing occurs'''

		lwidth = self.label.get_property('width') 
		bwidth = self.texture.get_property('width')
			
		new_w = None 
		if (lwidth > (bwidth - 14)):
			new_w = lwidth + 14
		elif (bwidth > 35) and (lwidth < (bwidth - 14)):
			new_w = max(35, lwidth + 14)

		if new_w is not None:
			self.set_size(new_w, self.texture.get_property('height'))

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		self.set_position(x, y)

		for c in self.connections_out:
			c.draw()
		
		for c in self.connections_in:
			c.draw()

	def set_size(self, w, h):
		self.size_w = w
		self.size_h = h 
	
		clutter.Group.set_size(self, w, h)	
		self.texture.set_size(w, h)
		self.texture.set_surface_size(w, h)
		self.texture.set_position(0, 0)
		self.texture.invalidate()

		self.draw_ports()

		for c in self.connections_out:
			c.draw()
		
		for c in self.connections_in:
			c.draw()

	def select(self):
		self.selected = True 
		self.texture.invalidate()

	def unselect(self):
		self.selected = False 
		self.texture.invalidate()

	def delete(self):
		for c in self.connections_out+self.connections_in:
			c.delete()

		PatchElement.delete(self)

	def make_edit_mode(self):
		return LabelEditMode(self.stage, self, self.label)

	def configure(self, params):
		if self.obj_args is None:
			self.label.set_text("%s" % (self.obj_type,))
		else:
			self.label.set_text("%s %s" % (self.obj_type, self.obj_args))
		PatchElement.configure(self, params)	

