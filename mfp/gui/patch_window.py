
from gi.repository import Clutter as clutter 

from text_element import TextElement
from processor_element import ProcessorElement
from connection_element import ConnectionElement 
from message_element import MessageElement
from enum_element import EnumElement
from plot_element import PlotElement

from mfp import MFPGUI 

from .input_manager import InputManager
from .modes.patch_edit import PatchEditMode
from .modes.patch_control import PatchControlMode 
from .modes.label_edit import LabelEditMode
from .modes.select_mru import SelectMRUMode 

class PatchWindow(object):
	def __init__(self):
		self.stage = clutter.Stage()
		self.group = clutter.Group()
		self.stage.add_actor(self.group)

		self.objects = [] 
		self.selected = None

		self.input_mgr = InputManager()
		
		self.color_unselected = clutter.Color()
		self.color_unselected.from_string('Black')

		self.color_selected = clutter.Color()
		self.color_selected.from_string('Red')

		self.color_bg = clutter.Color()
		self.color_bg.from_string("White")

		# configure clutter stage 
		self.stage.set_size(600, 400)
		self.stage.set_title("MFP")
		self.stage.set_color(self.color_bg)
		self.stage.set_property('user-resizable', True)
		self.zoom = 1.0
		self.view_x = 0
		self.view_y = 0

		print "PatchWindow: showing clutter stage"
		self.stage.show()
		
		# set up key and mouse handling 
		self.init_input()

	def init_input(self):
		def handler(stage, event):
			self.input_mgr.handle_event(stage, event)

		# hook up signals 
		self.stage.connect('button-press-event', handler)
		self.stage.connect('button-release-event', handler)
		self.stage.connect('key-press-event', handler)
		self.stage.connect('key-release-event', handler)
		self.stage.connect('motion-event', handler)
		self.stage.connect('enter-event', handler)
		self.stage.connect('leave-event', handler) 
		self.stage.connect('scroll-event', handler) 
		self.stage.connect('destroy', self.quit)

		# global keybindings 
		self.input_mgr.global_binding('C-e', self.toggle_major_mode, "toggle-major-mode")
		self.input_mgr.global_binding('C-q', self.quit, "quit")

		# set initial major mode 
		self.input_mgr.major_mode = PatchEditMode(self)

	def toggle_major_mode(self):
		if isinstance(self.input_mgr.major_mode, PatchEditMode):
			self.input_mgr.set_major_mode(PatchControlMode(self))
		else:
			self.input_mgr.set_major_mode(PatchEditMode(self))

	def register(self, element):
		self.objects.append(element)
		self.input_mgr.event_sources[element] = element 
		self.group.add_actor(element)
		if element.obj_id is not None:
			element.send_params()

	def unregister(self, element):
		print "unregister:", element, self.objects
		self.objects.remove(element)
		del self.input_mgr.event_sources[element]
		self.group.remove_actor(element)
		# FIXME hook
		SelectMRUMode.forget(element)

	def add_element(self, factory):
		b = factory(self, self.input_mgr.pointer_x, self.input_mgr.pointer_y)
		self.select(b)
		b.begin_edit()	

	def select(self, obj):
		if self.selected is not obj and self.selected is not None:
			self.unselect(self.selected)
		obj.select()
		self.selected = obj
		
		if isinstance(self.input_mgr.major_mode, PatchControlMode):
			obj.begin_control()

		# FIXME hook
		SelectMRUMode.touch(obj) 

	def unselect(self, obj):
		if self.selected is obj and obj is not None:
			obj.unselect()
			self.selected = None

	def unselect_all(self):
		if self.selected:
			self.selected.unselect()
			self.selected = None

	def select_next(self):
		if self.selected is None and len(self.objects) > 0:
			self.select(self.objects[0])
		cur_ind = self.objects.index(self.selected)
		self.select(self.objects[(cur_ind+1) % len(self.objects)])

	def select_prev(self):
		if self.selected is None and len(self.objects) > 0:
			self.select(self.objects[-1])
		cur_ind = self.objects.index(self.selected)
		self.select(self.objects[cur_ind-1])

	def select_mru(self):
		self.input_mgr.enable_minor_mode(SelectMRUMode(self))

	def move_selected(self, dx, dy):
		if self.selected is None:
			return
		self.selected.move(max(0, self.selected.position_x + dx*self.zoom),
					       max(0, self.selected.position_y + dy*self.zoom))
		if self.selected.obj_id is not None:
			self.selected.send_params()

	def delete_selected(self):
		if self.selected is None:
			return
		o = self.selected
		self.selected = None
		o.delete()

	def edit_selected(self):
		if self.selected is None:
			return
		self.selected.begin_edit()

	def rezoom(self):
		w, h = self.group.get_size()
		self.group.set_scale_full(self.zoom, self.zoom, w/2.0, h/2.0)
		self.group.set_position(self.view_x, self.view_y)

	def reset_zoom(self):
		self.zoom = 1.0
		self.view_x = 0
		self.view_y = 0
		self.rezoom()

	def zoom_out(self, ratio):
		if self.zoom >= 0.1:
			self.zoom *= ratio
			self.rezoom()
		
	def zoom_in(self, ratio):
		if self.zoom < 20:
			self.zoom *= ratio
			self.rezoom()

	def move_view(self, dx, dy):
		print "move_view:", dx, dy, self.zoom
		self.view_x += dx
		self.view_y += dy
		self.rezoom()

	def quit(self, *rest):
		clutter.main_quit()


