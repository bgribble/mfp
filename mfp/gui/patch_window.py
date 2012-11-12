
from gi.repository import Gtk, Clutter, GtkClutter 

from text_element import TextElement
from processor_element import ProcessorElement
from connection_element import ConnectionElement 
from message_element import MessageElement
from enum_element import EnumElement
from plot_element import PlotElement

from mfp import MFPGUI
from mfp.main import MFPCommand
from mfp import log 

from .input_manager import InputManager
from .console import ConsoleMgr 
from .modes.patch_edit import PatchEditMode
from .modes.patch_control import PatchControlMode 
from .modes.label_edit import LabelEditMode
from .modes.select_mru import SelectMRUMode 

class PatchWindow(object):
	def __init__(self):
		# load Glade ui
		self.builder = Gtk.Builder()
		self.builder.add_from_file("mfp/gui/mfp.glade")

		# install Clutter stage
		self.window = self.builder.get_object("main_window")
		self.embed = GtkClutter.Embed.new()
		self.embed.set_sensitive(True)
		self.embed.set_size_request(600, 400)
		self.stage = self.embed.get_stage()
		box = self.builder.get_object("stage_box")
		box.pack_start(self.embed, True, True, 0)

		self.console_view = self.builder.get_object("console_text")
		self.console_buffer = self.console_view.get_buffer()

		# create top-level group for stage 
		self.group = Clutter.Group()
		self.stage.add_actor(self.group)

		self.objects = [] 
		self.selected = None

		self.input_mgr = InputManager()
		self.console_mgr = ConsoleMgr("MFP interactive console", self.console_view,
							   self.console_buffer)
		self.console_mgr.start()

		# dumb colors 
		self.color_unselected = Clutter.Color()
		self.color_unselected.from_string('Black')
		self.color_selected = Clutter.Color()
		self.color_selected.from_string('Red')
		self.color_bg = Clutter.Color()
		self.color_bg.from_string("White")

		# configure Clutter stage 
		self.stage.set_color(self.color_bg)
		self.stage.set_property('user-resizable', True)
		self.zoom = 1.0
		self.view_x = 0
		self.view_y = 0

		# show top-level window
		self.stage.show()
		self.window.show_all()
		
		# make text entry area invisible 
		self.builder.get_object("text_entry_group").hide()
		
		# set up key and mouse handling 
		self.init_input()
		log.debug("PatchWindow is up")

	def init_input(self):
		def grab_handler(stage, event):
			if not self.embed.has_focus():
				self.embed.grab_focus()
			self.input_mgr.handle_event(stage, event)

		def handler(stage, event):
			self.input_mgr.handle_event(stage, event)

		self.embed.set_can_focus(True)
		self.embed.grab_focus()

		# hook up signals 
		self.stage.connect('button-press-event', grab_handler)
		self.stage.connect('button-release-event', grab_handler)
		self.stage.connect('key-press-event', grab_handler)
		self.stage.connect('key-release-event', grab_handler)
		self.stage.connect('destroy', self.quit)
		self.stage.connect('motion-event', handler)
		self.stage.connect('enter-event', handler)
		self.stage.connect('leave-event', handler) 
		self.stage.connect('scroll-event', grab_handler) 

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
		
		obj.begin_control()

		# FIXME hook
		SelectMRUMode.touch(obj) 

	def unselect(self, obj):
		if self.selected is obj and obj is not None:
			obj.end_control()
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
		self.view_x += dx
		self.view_y += dy
		self.rezoom()

	def quit(self, *rest):
		log.debug("Quit command from GUI or WM, shutting down")
		if self.console_mgr:
			self.console_mgr.quitreq = True 
			self.console_mgr.join()
			log.debug("Console thread reaped")

		MFPCommand().quit()

	def console_write(self, msg):
		tv = self.builder.get_object("console_text")
		buf = tv.get_buffer()
		iterator = buf.get_end_iter()
		buf.insert(iterator, msg, -1)
		tv.scroll_to_iter(iterator, 0, False, 0, 0)


	def add_log_entry(self, msg):
		tv = self.builder.get_object("log_text")
		buf = tv.get_buffer()
		iterator = buf.get_end_iter()
		buf.insert(iterator, msg, -1)
		tv.scroll_to_iter(iterator, 0, False, 0, 0)



