
import clutter 

from text_element import TextElement
from processor_element import ProcessorElement
from connection_element import ConnectionElement 
from message_element import MessageElement

from mfp import MFPGUI 

from .input_manager import InputManager
from .modes.patch_edit import PatchEditMode
from .modes.patch_control import PatchControlMode 
from .modes.label_edit import LabelEditMode
from .modes.select_mru import SelectMRUMode 

class PatchWindow(object):
	def __init__(self):
		self.stage = clutter.Stage()
		self.objects = [] 
		self.selected = None

		self.input_mgr = InputManager()
		
		self.color_unselected = clutter.color_from_string('Black')
		self.color_selected = clutter.color_from_string('Red')

		# configure clutter stage 
		self.stage.set_size(320, 240)
		self.stage.set_title("MFP")

		self.stage.show_all()
		
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
		self.input_mgr.event_sources[element.actor] = element 
		self.stage.add(element.actor)

	def unregister(self, element):
		print "unregister:", element, self.objects
		self.objects.remove(element)
		del self.input_mgr.event_sources[element.actor]
		self.stage.remove(element.actor)
		SelectMRUMode.forget(element)

	def add_processor(self):
		b = ProcessorElement(self, self.input_mgr.pointer_x, self.input_mgr.pointer_y)
		self.select(b)
		self.input_mgr.enable_minor_mode(LabelEditMode(self, b, b.label))

	def add_text(self):
		b = TextElement(self, self.input_mgr.pointer_x, self.input_mgr.pointer_y)
		self.select(b)
		self.input_mgr.enable_minor_mode(LabelEditMode(self, b, b.label, multiline=True))

	def add_message(self):
		b = MessageElement(self, self.input_mgr.pointer_x, self.input_mgr.pointer_y)
		self.select(b)
		self.input_mgr.enable_minor_mode(LabelEditMode(self, b, b.label))

	def select(self, obj):
		if self.selected is not obj and self.selected is not None:
			self.unselect(self.selected)
		obj.select()
		self.selected = obj
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
		self.selected.move(max(0, self.selected.position_x + dx),
					       max(0, self.selected.position_y + dy))

	def delete_selected(self):
		if self.selected is None:
			return
		o = self.selected
		self.selected = None
		o.delete()

	def quit(self, *rest):
		clutter.main_quit()


