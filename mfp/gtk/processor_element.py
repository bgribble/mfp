#! /usr/bin/env python2.6
'''
processor_element.py
A patch element corresponding to a signal or control processor 
'''

import clutter 
from patch_element import PatchElement 

class ProcessorElement (PatchElement):
	def __init__(self, window, x, y):
		PatchElement.__init__(self, window, x, y)
		
		self.proc_type = None
		self.proc_args = None 
		self.connections = [] 
		self.editable = False 

		# create elements 
		self.actor = clutter.Rectangle()
		self.label = clutter.Text()

		# configure rectangle box 
		self.actor.set_size(50, 20)
		self.actor.set_border_width(2)
		self.actor.set_border_color(window.color_unselected)
		self.actor.set_reactive(True)

		# configure label
		self.label.set_activatable(True)
		self.label.set_reactive(True)
		self.label.set_color(window.color_unselected) 
		self.label.connect('activate', self.text_activate_cb)
		self.label.connect('text-changed', self.text_changed_cb)

		self.move(x, y)

		# add components to stage 
		self.stage.stage.add(self.actor)
		self.stage.stage.add(self.label)
		self.stage.stage.set_key_focus(self.label)

	def text_activate_cb(self, *args):
		self.label.set_editable(False)
		self.stage.stage.set_key_focus(None)

		t = self.label.get_text()
		parts = t.split(' ', 1)
		self.proc_type = parts[0]
		if len(parts) > 1:
			self.proc_args = parts[1]

		print "ProcessorElement: processor=%s, args=%s" % (self.proc_type, self.proc_args)
		print self.label.get_text()
		self.editable = False 

	def text_changed_cb(self, *args):
		lwidth = self.label.get_property('width') 
		bwidth = self.actor.get_property('width')

		if (lwidth > (bwidth - 16)) or (bwidth >= 50 and (lwidth < (bwidth - 16))):
			self.actor.set_size(lwidth + 16, self.actor.get_property('height'))

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		self.actor.set_position(x, y)
		self.label.set_position(x+4, y+1)

	def select(self):
		self.actor.set_border_color(self.stage.color_selected)

	def unselect(self):
		self.actor.set_border_color(self.stage.color_unselected)

	def toggle_edit(self):
		if self.editable:
			self.label.set_editable(False)
			self.stage.stage.set_key_focus(None)
			self.editable = False 
		else:
			self.label.set_editable(True)
			self.stage.stage.set_key_focus(self.label)
			self.editable = True



