
from gi.repository import Gtk, Clutter, GtkClutter, Pango

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

		# install Clutter stage in Gtk window
		self.window = self.builder.get_object("main_window")
		self.embed = GtkClutter.Embed.new()
		self.embed.set_sensitive(True)
		self.embed.set_size_request(600, 400)
		self.stage = self.embed.get_stage()
		box = self.builder.get_object("stage_box")
		box.pack_start(self.embed, True, True, 0)

		# significant widgets we will be dealing with later 
		self.console_view = self.builder.get_object("console_text")
		self.log_view = self.builder.get_object("log_text") 

		# objects for stage -- self.group gets moved to adjust 
		# the view, so anything not in it will be static on the stage 
		self.group = Clutter.Group()
		self.hud_text = Clutter.Text() 
		self.hud_animation = None 
		self.hud_text.set_property("opacity", 0)
		self.stage.add_actor(self.group)
		self.stage.add_actor(self.hud_text) 

		self.objects = [] 
		self.selected = None

		self.input_mgr = InputManager(self)
		self.console_mgr = ConsoleMgr("MFP interactive console", self.console_view)
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
		
		# set tab stops on keybindings view 
		ta = Pango.TabArray.new(1, True)
		ta.set_tab(0, Pango.TabAlign.LEFT, 120)
		self.builder.get_object("key_bindings_text").set_tabs(ta)

		# set up key and mouse handling 
		self.init_input()

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
		self.display_bindings()

	def stage_pos(self, x, y):
		success, new_x, new_y = self.group.transform_stage_point(x, y)
		if success:
			return (new_x, new_y) 
		else:
			return (x, y)

	def display_bindings(self):
		lines = ["Active key/mouse bindings"]
		for m in self.input_mgr.minor_modes: 
			lines.append("\nMinor mode: " + m.description)
			for b in m.directory():
				lines.append("%s\t%s" % (b[0], b[1]))

		m = self.input_mgr.major_mode
		lines.append("\nMajor mode: " + m.description)
		for b in m.directory():
			lines.append("%s\t%s" % (b[0], b[1]))

		lines.append("\nGlobal bindings:")
		m = self.input_mgr.global_mode 
		for b in m.directory():
			lines.append("%s\t%s" % (b[0], b[1]))

		txt = '\n'.join(lines)

		tv = self.builder.get_object("key_bindings_text")
		buf = tv.get_buffer()
		iterator = buf.get_end_iter()
		buf.delete(buf.get_start_iter(), buf.get_end_iter())
		buf.insert(buf.get_end_iter(), txt) 


	def toggle_major_mode(self):
		if isinstance(self.input_mgr.major_mode, PatchEditMode):
			self.input_mgr.set_major_mode(PatchControlMode(self))
		else:
			self.input_mgr.set_major_mode(PatchEditMode(self))
		return True 

	def register(self, element):
		self.objects.append(element)
		self.input_mgr.event_sources[element] = element 
		self.group.add_actor(element)
		if element.obj_id is not None:
			element.send_params()

	def unregister(self, element):
		if self.selected == element:
			self.unselect(element)

		self.objects.remove(element)
		del self.input_mgr.event_sources[element]
		self.group.remove_actor(element)
		# FIXME hook
		SelectMRUMode.forget(element)

	def add_element(self, factory):
		b = factory(self, self.input_mgr.pointer_x, self.input_mgr.pointer_y)
		self.select(b)
		b.begin_edit()	
		return True 

	def select(self, obj):
		if self.selected is not obj and self.selected is not None:
			self.unselect(self.selected)
		obj.select()
		self.selected = obj
		
		obj.begin_control()

		# FIXME hook
		SelectMRUMode.touch(obj) 
		return True 

	def unselect(self, obj):
		if self.selected is obj and obj is not None:
			obj.end_control()
			obj.unselect()
			self.selected = None
		return True 

	def unselect_all(self):
		if self.selected:
			self.selected.end_control()
			self.selected.unselect()
			self.selected = None
		return True 

	def select_next(self):
		if len(self.objects) == 0:
			return False 
		elif self.selected is None and len(self.objects) > 0:
			self.select(self.objects[0])
			return True 
		else:
			cur_ind = self.objects.index(self.selected)
			self.select(self.objects[(cur_ind+1) % len(self.objects)])
			return True 

	def select_prev(self):
		if len(self.objects) == 0:
			return False 
		elif self.selected is None and len(self.objects) > 0:
			self.select(self.objects[-1])
			return True 
		else:
			cur_ind = self.objects.index(self.selected)
			self.select(self.objects[cur_ind-1])
			return True 

	def select_mru(self):
		self.input_mgr.enable_minor_mode(SelectMRUMode(self))
		return True 

	def move_selected(self, dx, dy):
		if self.selected is None:
			return
		self.selected.move(max(0, self.selected.position_x + dx*self.zoom),
					       max(0, self.selected.position_y + dy*self.zoom))
		if self.selected.obj_id is not None:
			self.selected.send_params()
		return True 

	def delete_selected(self):
		if self.selected is None:
			return
		o = self.selected
		o.delete()
		return True 

	def edit_selected(self):
		if self.selected is None:
			return True
		self.selected.begin_edit()
		return True

	def rezoom(self):
		w, h = self.group.get_size()
		self.group.set_scale_full(self.zoom, self.zoom, w/2.0, h/2.0)
		self.group.set_position(self.view_x, self.view_y)

	def reset_zoom(self):
		self.zoom = 1.0
		self.view_x = 0
		self.view_y = 0
		self.rezoom()
		return True 

	def zoom_out(self, ratio):
		if self.zoom >= 0.1:
			self.zoom *= ratio
			self.rezoom()
		return True 
		
	def zoom_in(self, ratio):
		if self.zoom < 20:
			self.zoom *= ratio
			self.rezoom()
		return True 

	def move_view(self, dx, dy):
		self.view_x += dx
		self.view_y += dy
		self.rezoom()
		return True 

	def quit(self, *rest):
		log.debug("Quit command from GUI or WM, shutting down")
		if self.console_mgr:
			self.console_mgr.quitreq = True 
			self.console_mgr.join()
			log.debug("Console thread reaped")

		MFPCommand().quit()
		return True 

	def console_write(self, msg):
		buf = self.console_view.get_buffer()
		iterator = buf.get_end_iter()
		buf.insert(iterator, msg, -1)
		self.console_view.scroll_to_iter(iterator, 0, False, 0, 0)

	def log_write(self, msg):
		buf = self.log_view.get_buffer()
		iterator = buf.get_end_iter()
		buf.insert(iterator, msg, -1)
		self.log_view.scroll_to_iter(iterator, 0, False, 0, 0)
	
	def hud_write(self, msg, disp_time=2.0):
		def anim_complete(*args):
			self.hud_animation = None 

		if self.hud_animation is not None: 
			self.hud_animation.completed()
		
		self.hud_text.set_position(10, self.stage.get_height() - 25)
		self.hud_text.set_markup(msg)
		self.hud_text.set_property("opacity", 255)

		self.hud_animation = self.hud_text.animatev(Clutter.AnimationMode.EASE_IN_CUBIC, 
												 disp_time * 1000.0, 
												 [ 'opacity' ], [ 0 ])
		self.hud_animation.connect_after("completed", anim_complete)


