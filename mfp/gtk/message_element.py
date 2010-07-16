#! /usr/bin/env python2.6
'''
message_element.py
A patch element corresponding to a clickable message
'''

import clutter 
import cairo
import math 
from patch_element import PatchElement
from mfp import MFPGUI

class MessageElement (PatchElement):
	def __init__(self, window, x, y):
		PatchElement.__init__(self, window, x, y)

		self.proc_id = None 	
		self.message_text = None 
		self.connections_out = [] 
		self.connections_in = [] 
		self.editable = False 

		# create elements
		self.actor = clutter.Group()
		self.texture = clutter.CairoTexture(35, 20)
		self.label = clutter.Text()

		self.actor.set_reactive(True)
		self.actor.add(self.texture)
		self.actor.add(self.label)

		# configure rectangle box 
		self.draw_border()

		# configure label
		self.label.set_position(4, 1)
		self.label.set_color(window.color_unselected) 
		self.label.connect('text-changed', self.text_changed_cb)

		# click handler 
		self.actor.connect('button-press-event', self.button_press_cb)
		
		self.move(x, y)

		# add components to stage 
		self.stage.register(self)

	def draw_border(self):
		w = self.texture.get_property('surface_width')-2
		h = self.texture.get_property('surface_height')-2
		print "draw_border: w=%s, h=%s" % (w, h)
		self.texture.clear()
		ct = self.texture.cairo_create()
		if self.selected: 
			ct.set_source_color(self.stage.color_selected)
		else:
			ct.set_source_color(self.stage.color_unselected)
		ct.translate(0.5, 0.5)
		ct.move_to(1,1)
		ct.line_to(1, h)
		ct.line_to(w, h)
		ct.curve_to(w-8, h-8, w-8, 8, w, 1)
		ct.line_to(1,1)
		ct.close_path()
		ct.stroke()

	def button_press_cb(self, *args):
		print "button press", args
		MFPGUI.send_bang(self.proc_id, 0) 

	def update_label(self, *args):
		self.message_text = self.label.get_text()

		print "MessageElement: obj=%s" % (self.message_text)
		self.proc_id = MFPGUI.create("var", self.message_text)
		if self.proc_id is None:
			print "MessageElement: could not create message obj"

	def text_changed_cb(self, *args):
		lwidth = self.label.get_property('width') 
		bwidth = self.texture.get_property('surface_width')
	
		new_w = None 
		if (lwidth > (bwidth - 20)):
			new_w = lwidth + 20
		elif (bwidth > 35) and (lwidth < (bwidth - 20)):
			new_w = max(35, lwidth + 20)

		if new_w is not None:
			self.texture.set_size(new_w, self.texture.get_height())
			self.texture.set_surface_size(int(new_w), self.texture.get_property('surface_height'))
			self.draw_border()

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		self.actor.set_position(x, y)

		for c in self.connections_out:
			c.draw()
		
		for c in self.connections_in:
			c.draw()

	def select(self):
		#self.actor.set_border_color(self.stage.color_selected)
		self.selected = True 
		self.draw_border()

	def unselect(self):
		#self.actor.set_border_color(self.stage.color_unselected)
		self.selected = False 
		self.draw_border()

	def toggle_edit(self):
		if self.editable:
			self.label.set_editable(False)
			self.stage.stage.set_key_focus(None)
			self.editable = False 
		else:
			self.label.set_editable(True)
			self.stage.stage.set_key_focus(self.label)
			self.editable = True



