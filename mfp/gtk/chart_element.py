#! /usr/bin/env python
'''
chart_element.py
A patch element corresponding to a chart
'''

from gi.repository import Clutter as clutter 
import math 
from patch_element import PatchElement
from mfp import MFPGUI
from input_mode import InputMode
from .modes.label_edit import LabelEditMode
from .xyplot import XYPlot

class ChartElement (PatchElement):
	element_type = "chart"

	# constants 
	label_off_x = 3
	label_off_y = 0 

	INIT_WIDTH = 320
	INIT_HEIGHT = 240
	LABEL_SPACE = 15

	def __init__(self, window, x, y, params={}):
		PatchElement.__init__(self, window, x, y)
		
		# display elements 
		self.actor = None
		self.rect = None
		self.label = None
		self.label_text = None 
		self.xyplot = None

		# create display 
		self.create_display()
		self.set_size(self.INIT_WIDTH, self.INIT_HEIGHT+self.LABEL_SPACE)
		self.move(x, y)
		self.update()

		# add components to stage 
		self.stage.register(self)

	def create_display(self):
		self.actor = clutter.Group()
		self.rect = clutter.Rectangle()
		self.label = clutter.Text()

		# rectangle box 
		self.rect.set_border_width(2)
		self.rect.set_border_color(self.stage.color_unselected)
		self.rect.set_reactive(False)

		# label
		self.label.set_position(self.label_off_x, self.label_off_y)
		self.label.set_color(self.stage.color_unselected) 
		self.label.connect('text-changed', self.label_changed_cb)
		self.label.set_reactive(False)

		self.xyplot = XYPlot(self.actor, self.INIT_WIDTH, self.INIT_HEIGHT, "")
		self.xyplot.set_position(0, self.LABEL_SPACE)

		self.actor.add_actor(self.rect)
		self.actor.add_actor(self.label)
		self.actor.set_reactive(True)

	def update(self):
		# FIXME not-created style (dashed lines?)

		self.draw_ports()

	def get_label(self):
		return self.label

	def label_edit_start(self):
		# FIXME set label to editing style 
		pass

	def label_edit_finish(self, *args):
		t = self.label.get_text()

		if t != self.label_text:
			parts = t.split(' ', 1)
			self.obj_type = parts[0]
			if len(parts) > 1:
				self.obj_args = parts[1]

			print "ChartElement: type=%s, args=%s" % (self.obj_type, self.obj_args)
			self.create(self.element_type, None)
			if self.obj_id is None:
				print "ChartElement: could not create", self.obj_type, self.obj_args
			else:
				self.send_params()
				self.draw_ports()

		# FIXME set label to non-editing style 

		self.update()

	def label_changed_cb(self, *args):
		'''called by clutter when label.set_text or editing occurs'''

		lwidth = self.label.get_property('width') 
		bwidth = self.rect.get_property('width')
			
		new_w = None 
		if (lwidth > (bwidth - 14)):
			new_w = lwidth + 14
		elif (bwidth > 35) and (lwidth < (bwidth - 14)):
			new_w = max(35, lwidth + 14)

		if new_w is not None:
			self.set_size(new_w, self.rect.get_property('height'))

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		self.actor.set_position(x, y)

		for c in self.connections_out:
			c.draw()
		
		for c in self.connections_in:
			c.draw()

	def set_size(self, w, h):
		self.size_w = w
		self.size_h = h 

		self.rect.set_size(w, h)
		self.rect.set_position(0, 0)
		self.xyplot.set_size(w, h-self.LABEL_SPACE)

		self.draw_ports()

		for c in self.connections_out:
			c.draw()
		
		for c in self.connections_in:
			c.draw()

	def select(self):
		self.selected = True 
		self.rect.set_border_color(self.stage.color_selected)

	def unselect(self):
		self.selected = False 
		self.rect.set_border_color(self.stage.color_unselected)

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

		action = params.get("_chart_action")
		if action == "clear":
			self.xyplot.clear()
		elif action == "add":
			newpt = params.get("_chart_data")
			self.xyplot.append(newpt)
			print "CHART: data = ", self.xyplot.points
			self.xyplot.update()
		PatchElement.configure(self, params)	

