#! /usr/bin/env python
'''
patch_window.py
The main MFP window and associated code 
'''

from gi.repository import Gtk, GObject, Clutter, GtkClutter, Pango

from text_element import TextElement
from processor_element import ProcessorElement
from connection_element import ConnectionElement 
from message_element import MessageElement
from enum_element import EnumElement
from plot_element import PlotElement
from patch_element import PatchElement 
from patch_layer import PatchLayer 

from mfp import MFPGUI
from mfp.main import MFPCommand
from mfp import log 

from .input_manager import InputManager
from .console import ConsoleMgr 
from .modes.patch_edit import PatchEditMode
from .modes.patch_control import PatchControlMode 
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
		self.object_view = self.builder.get_object("object_tree") 
		self.layer_view = self.builder.get_object("layer_tree") 
		self.layer_store = None 
		self.object_store = None 

		# objects for stage -- self.group gets moved/scaled to adjust 
		# the view, so anything not in it will be static on the stage 
		self.group = Clutter.Group()
		self.hud_text = Clutter.Text() 
		self.hud_animation = None 
		self.hud_text.set_property("opacity", 0)
		self.autoplace_marker = None 
		self.stage.add_actor(self.group)
		self.stage.add_actor(self.hud_text) 

		# self.objects is PatchElement subclasses represented the currently-displayed
		# patch 
		self.objects = [] 
		self.selected = None
		self.layers = [ PatchLayer(self, "Default") ] 
		self.selected_layer = None  

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
		
		# set up key and mouse handling 
		self.init_input()
		self.init_layer_view()
		self.init_object_view()
		self.layer_select(0)

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
		self.input_mgr.global_binding("PGUP", self.layer_select_up, "Select higher layer")
		self.input_mgr.global_binding("PGDN", self.layer_select_down, "Select lower layer")
		self.input_mgr.global_binding("C-n", self.layer_new, "Create new layer")
		self.input_mgr.global_binding("C-N", self.layer_new_scope, 
								      "Create new layer in a new scope")
		self.input_mgr.global_binding('C-e', self.toggle_major_mode, "Toggle edit/control")
		self.input_mgr.global_binding('C-q', self.quit, "Quit")

		# set initial major mode 
		self.input_mgr.major_mode = PatchEditMode(self)

		# set tab stops on keybindings view 
		ta = Pango.TabArray.new(1, True)
		ta.set_tab(0, Pango.TabAlign.LEFT, 120)
		self.builder.get_object("key_bindings_text").set_tabs(ta)

		# show keybindings 
		self.display_bindings()

	def init_layer_view(self):
		def select_cb(selection):
			model, iter = selection.get_selected()
			if iter is None:
				return 
			row = self.layer_store.get_value(iter, 0)
			if row != self.selected_layer:
				self.layer_select(row, do_update=False)

		self.layer_store = Gtk.TreeStore(GObject.TYPE_INT, GObject.TYPE_STRING,
										 GObject.TYPE_STRING)
		self.layer_view.set_model(self.layer_store)
		self.layer_view.get_selection().connect("changed", select_cb)

		for header, num in [("Num", 0), ("Layer", 1), ("Scope", 2)]:
			r = Gtk.CellRendererText()
			col = Gtk.TreeViewColumn(header, r, text=num)
			self.layer_view.append_column(col)

		self.layer_store_update()

	def init_object_view(self):
		def select_cb(selection):
			model, iter = selection.get_selected()
			if iter is None: 
				self.unselect_all()
			else:
				obj = self.object_store.get_value(iter, 1) 
				if isinstance(obj, PatchElement) and obj is not self.selected:
					self.select(obj)

		self.object_store = Gtk.TreeStore(GObject.TYPE_STRING, GObject.TYPE_PYOBJECT)
		self.object_view.set_model(self.object_store)
		self.object_view.get_selection().connect("changed", select_cb)

		for header, num in [("Name", 0)]:
			r = Gtk.CellRendererText()
			col = Gtk.TreeViewColumn(header, r, text=num)
			self.object_view.append_column(col)

	def layer_select_up(self):
		if self.selected_layer > 0:
			self.layer_select(self.selected_layer - 1)
			return True 
	
	def layer_select_down(self):
		if self.selected_layer < (len(self.layers)-1):
			self.layer_select(self.selected_layer + 1)
			return True 

	def layer_select(self, layer_num, do_update=True):
		if self.selected_layer is not None:
			self.layers[self.selected_layer].hide()
		self.selected_layer = layer_num 
		ll = self.layers[self.selected_layer]
		ll.show()
		self.hud_write("Layer %s (lexical scope '%s')" % (ll.name, ll.scope))
		if do_update:
			self.layer_selection_update()

	def layer_new(self):
		self.layers.append(PatchLayer(self, "Layer %d" % len(self.layers)))
		self.layer_store_update()
		self.layer_selection_update()
		return True 

	def layer_new_scope(self):
		l = PatchLayer(self, "Layer %d" % len(self.layers))
		l.scope = l.name.replace(" ", "_").lower()
		MFPCommand().add_scope(l.scope)

		self.layers.append(l)
		self.layer_store_update()
		self.layer_selection_update()
		return True 

	def layer_selection_update(self):
		model, iter = self.layer_view.get_selection().get_selected()

		if iter is None or self.layer_store.get_value(iter, 0) != self.selected_layer:
			liter = self.layer_store.iter_nth_child(None, self.selected_layer)
			spath = self.layer_store.get_path(liter)
			if spath is not None:
				self.layer_view.get_selection().select_path(spath)

	def layer_store_update(self):
		self.layer_store.clear()
		for layernum in range(len(self.layers)):
			liter = self.layer_store.append(None)
			self.layer_store.set_value(liter, 0, layernum)
			self.layer_store.set_value(liter, 1, self.layers[layernum].name)
			self.layer_store.set_value(liter, 2, self.layers[layernum].scope or "Patch")


	def object_selection_update(self):
		found = []
		def	check(model, path, it, data):
			if self.object_store.get_value(it, 1) == self.selected:
				found[:] = path
				return True
			return False 

		model, iter = self.object_view.get_selection().get_selected()

		if iter is None or self.object_store.get_value(iter, 1) != self.selected: 
			self.object_store.foreach(check, None)
			if found:
				self.object_view.get_selection().select_path(found[0])

	def object_store_update(self):
		scopes = {} 
		self.object_store.clear()

		for s in self.layers:
			if s.scope is None:
				continue 
			oiter = self.object_store.append(None)
			self.object_store.set_value(oiter, 0, s.scope)
			self.object_store.set_value(oiter, 1, s)
			scopes[s.scope] = oiter

		for o in self.objects:
			if o.obj_name is None:
				continue

			if o.layer.scope is None:
				parent = None 
			else:
				parent = scopes.get(o.layer.scope)
			oiter = self.object_store.append(parent)
			self.object_store.set_value(oiter, 0, o.obj_name)
			self.object_store.set_value(oiter, 1, o)

	def active_layer(self):
		return self.layers[self.selected_layer]

	def active_group(self):
		return self.layers[self.selected_layer].group 

	def ready(self):
		if self.window and self.window.get_realized():
			return True
		else:
			return False 

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


	def show_autoplace_marker(self, x, y):
		if self.autoplace_marker is None:
			self.autoplace_marker = Clutter.Text()
			self.autoplace_marker.set_text("+")
			self.active_group().add_actor(self.autoplace_marker)
		self.autoplace_marker.set_position(x, y)
		self.autoplace_marker.set_depth(-10)
		self.autoplace_marker.show()

	def hide_autoplace_marker(self):
		if self.autoplace_marker:
			self.autoplace_marker.hide()

	def toggle_major_mode(self):
		if isinstance(self.input_mgr.major_mode, PatchEditMode):
			self.input_mgr.set_major_mode(PatchControlMode(self))
		else:
			self.input_mgr.set_major_mode(PatchEditMode(self))
		return True 

	def register(self, element):
		self.objects.append(element)
		self.input_mgr.event_sources[element] = element 
		self.active_group().add_actor(element)
		element.layer = self.active_layer()
		if element.obj_id is not None:
			element.send_params()
		self.object_store_update()

	def unregister(self, element):
		if self.selected == element:
			self.unselect(element)

		element.layer = None 
		self.objects.remove(element)
		del self.input_mgr.event_sources[element]
		self.active_group().remove_actor(element)
		self.object_store_update()

		# FIXME hook
		SelectMRUMode.forget(element)

	def refresh(self, element): 
		self.object_store_update()

	def add_element(self, factory, x=None, y=None):
		if x is None:
			x = self.input_mgr.pointer_x
		if y is None:
			y = self.input_mgr.pointer_y
		
		b = factory(self, x, y)
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

		self.object_selection_update()
		return True 

	def unselect(self, obj):
		if self.selected is obj and obj is not None:
			obj.end_control()
			obj.unselect()
			self.selected = None
			self.object_selection_update()
		return True 

	def unselect_all(self):
		if self.selected:
			self.selected.end_control()
			self.selected.unselect()
			self.selected = None
			self.object_selection_update()
		return True 

	def select_next(self):
		if len(self.objects) == 0:
			return False 

		selectable = [ o for o in self.objects if not isinstance(o, ConnectionElement)]
		if self.selected is None and len(selectable) > 0:
			self.select(selectable[0])
			return True 
		else:
			cur_ind = selectable.index(self.selected)
			self.select(selectable[(cur_ind+1) % len(selectable)])
			return True 

	def select_prev(self):
		if len(self.objects) == 0:
			return False 

		selectable = [ o for o in self.objects if not isinstance(o, ConnectionElement)]
		if self.selected is None and len(selectable) > 0:
			self.select(selectable[-1])
			return True 
		else:
			cur_ind = selectable.index(self.selected) 
			self.select(selectable[cur_ind-1])
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
		mark = buf.get_mark("console_mark")
		if mark is None:
			mark = Gtk.TextMark.new("console_mark", False)
			buf.add_mark(mark, iterator)

		buf.insert(iterator, msg, -1)
		iterator = buf.get_end_iter()
		buf.move_mark(mark, iterator)
		self.console_view.scroll_to_mark(mark, 0, True, 1.0, 0.9)

	def log_write(self, msg):
		# this is a bit complicated so that we ensure scrolling is 
		# reliable... scroll_to_iter can act odd sometimes 
		buf = self.log_view.get_buffer()
		iterator = buf.get_end_iter()
		mark = buf.get_mark("log_mark")
		if mark is None:
			mark = Gtk.TextMark.new("log_mark", False)
			buf.add_mark(mark, iterator)
		buf.insert(iterator, msg, -1)
		iterator = buf.get_end_iter()
		buf.move_mark(mark, iterator)
		self.log_view.scroll_to_mark(mark, 0, True, 0, 0.9)
	
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


