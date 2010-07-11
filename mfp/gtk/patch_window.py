
import clutter 

from text_element import TextElement
from processor_element import ProcessorElement
from connection_element import ConnectionElement 
from message_element import MessageElement

from mfp import MFPGUI 

from input_manager import InputManager
from modes.patch_edit import PatchEditMode
from modes.patch_control import PatchControlMode 
from modes.label_edit import LabelEditMode

class PatchWindow(object):

	def __init__(self):
		self.stage = clutter.Stage()
		self.objects = [] 
		self.selected = None
		
		self.input_mgr = InputManager()
		
		self.color_unselected = clutter.color_from_string('Black')
		self.color_selected = clutter.color_from_string('Red')

		# used while building a connection
		self.conn_mode = None 
		self.conn_start_obj = None
		self.conn_start_port = None
		self.conn_end_obj = None
		self.conn_end_port = None

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

	def add_processor(self):
		b = ProcessorElement(self, self.input_mgr.pointer_x, self.input_mgr.pointer_y)
		self.objects.append(b)
		self.select(b)
		self.input_mgr.enable_minor_mode(LabelEditMode(self, b.label))

	def add_text(self):
		b = TextElement(self, self.pointer_x, self.pointer_y)
		self.objects.append(b)
		self.select(b)
		b.toggle_edit()

	def add_message(self):
		b = MessageElement(self, self.pointer_x, self.pointer_y)
		self.objects.append(b)
		self.select(b)
		b.toggle_edit()

	def select(self, obj):
		if self.conn_mode == 'c':
			self.conn_end_obj = obj
		elif self.conn_mode == 'C':
			self.conn_start_obj = obj

		if self.selected is not obj and self.selected is not None:
			self.selected.unselect()
		obj.select()
		self.selected = obj
	
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

	def dispatch_key(self, key):
		# should handle this with a dict of keysym to handler 
		# with contexts (modes) 

		# global functions 
		if key == 'C-q':
			self.quit()
		elif key == 'C-s':
			self.save()

		# creating elements 
		elif key == 'C-a':
			self.add_processor()
		elif key == 'C-t':
			self.add_text()
		elif key == 'C-m':
			self.add_message()

		# selection/editing 
		elif key == 'C-u':
			if self.selected:
				self.selected.unselect()
				self.selected = None
		elif key == 'S-C-u':
			if self.selected:
				self.selected.toggle_edit()
		elif key == 'TAB':
			self.select_next()
		elif key == 'S-TAB':
			self.select_prev()

		# connections 
		elif key == 'c':
			if self.selected:
				self.conn_mode = 'c'
				self.conn_start_obj = self.selected 
				self.conn_end_obj = None
				self.conn_start_port = 0
				self.conn_end_port = 0
		elif key == 'S-c':
			if self.selected:
				self.conn_mode = 'C'
				self.conn_start_obj = None
				self.conn_end_obj = self.selected
				self.conn_start_port = 0
				self.conn_end_port = 0

		elif key in ('1', '2', '3', '4', '5', '6', '7', '8', '9'):
			if self.conn_mode == 'c':
				if self.conn_end_obj is None:
					self.conn_start_port = int(key) - 1
				else:
					self.conn_end_port = int(key) - 1
			elif self.conn_mode == 'C':
				if self.conn_start_obj is None:
					self.conn_end_port = int(key) - 1
				else:
					self.conn_start_port = int(key) - 1
		elif key == 'RET':
			print self.conn_mode, self.conn_start_obj, self.conn_end_obj
			if self.conn_mode is not None:
				if self.conn_start_obj is not None and self.conn_end_obj is not None:
					print "Making connection:"
					print self.conn_start_obj, self.conn_start_port, '-->', self.conn_end_obj, self.conn_end_port
		
					if MFPGUI.connect(self.conn_start_obj.proc_id, self.conn_start_port,
					                  self.conn_end_obj.proc_id, self.conn_end_port):
						c = ConnectionElement(self, self.conn_start_obj, self.conn_start_port,
											  self.conn_end_obj, self.conn_end_port)
						self.conn_start_obj.connections_out.append(c)
						self.conn_end_obj.connections_in.append(c)
					else:
						print "Cannot make connection"

					self.conn_mode = None 
		# movement 
		elif key == 'UP':
			self.move_selected(0, -1)	
		elif key == 'DOWN':
			self.move_selected(0, 1)
		elif key == 'LEFT':
			self.move_selected(-1, 0)	
		elif key == 'RIGHT':
			self.move_selected(1, 0)
		elif key == 'S-UP':
			self.move_selected(0, -5)	
		elif key == 'S-DOWN':
			self.move_selected(0, 5)
		elif key == 'S-LEFT':
			self.move_selected(-5, 0)	
		elif key == 'S-RIGHT':
			self.move_selected(5, 0)
		elif key == 'C-UP':
			self.move_selected(0, -25)	
		elif key == 'C-DOWN':
			self.move_selected(0, 25)
		elif key == 'C-LEFT':
			self.move_selected(-25, 0)	
		elif key == 'C-RIGHT':
			self.move_selected(25, 0)

	def move_selected(self, dx, dy):
		if self.selected is None:
			return
		self.selected.move(max(0, self.selected.position_x + dx),
					       max(0, self.selected.position_y + dy))
	def quit(self, *rest):
		clutter.main_quit()


