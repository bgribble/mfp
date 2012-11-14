#! /usr/bin/env python2.6
'''
gui.py
GTK/clutter gui for MFP -- main thread

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import threading 
import os
from request import Request
from singleton import Singleton
from rpc_wrapper import RPCWrapper, rpcwrap
from main import MFPCommand
from . import log 

def gui_init(pipe):
	import os
	log.log_module = "gui"
	log.debug("GUI thread started, pid =", os.getpid())
	pipe.on_finish(gui_finish)
	RPCWrapper.pipe = pipe
	RPCWrapper.node_id = "Clutter GUI"
	GUICommand.local = True
	MFPCommand.local = False
	MFPGUI()

def gui_finish():
	MFPGUI().finish()

class GUICommand (RPCWrapper):
	@rpcwrap
	def ready(self):
		if MFPGUI().appwin is not None:
			return True
		else:
			return False

	@rpcwrap
	def log_write(self, msg): 
		MFPGUI().clutter_do(lambda: self._log_write(msg))
		return True 

	def _log_write(self, msg):
		MFPGUI().appwin.log_write(msg)

	@rpcwrap
	def console_write(self, msg): 
		MFPGUI().clutter_do(lambda: self._console_write(msg))
		return True 

	def _console_write(self, msg):
		MFPGUI().appwin.console_write(msg)

	@rpcwrap
	def hud_write(self, msg): 
		MFPGUI().clutter_do(lambda: self._hud_write(msg))
		return True 

	def _hud_write(self, msg):
		MFPGUI().appwin.hud_write(msg)

	@rpcwrap
	def finish(self):
		MFPGUI().finish()

	@rpcwrap
	def configure(self, obj_id, params):
		MFPGUI().clutter_do(lambda: self._configure(obj_id, params))
		return True

	def _configure(self, obj_id, params):
		obj = MFPGUI().recall(obj_id)
		obj.configure(params)

	@rpcwrap
	def command(self, obj_id, cmd, cmd_params):
		MFPGUI().clutter_do(lambda: self._command(obj_id, cmd, cmd_params))
		return True 

	def _command(self, obj_id, cmd, cmd_params):
		obj = MFPGUI().recall(obj_id)
		obj.command(cmd, cmd_params)

	@rpcwrap
	def create(self, obj_type, obj_args, obj_id, params): 
		MFPGUI().clutter_do(lambda: self._create(obj_type, obj_args, obj_id, params))

	def _create(self, obj_type, obj_args, obj_id, params): 
		from .gui.processor_element import ProcessorElement
		from .gui.message_element import MessageElement
		from .gui.text_element import TextElement
		from .gui.enum_element import EnumElement
		from .gui.plot_element import PlotElement 

		elementtype = params.get('element_type')
		log.debug("create:", obj_id, elementtype, params)

		ctors = {
			'processor': ProcessorElement,
			'message': MessageElement,
			'text': TextElement,
			'enum': EnumElement,
			'plot': PlotElement
		}
		ctor = ctors.get(elementtype)
		if ctor:
			o = ctor(MFPGUI().appwin, params.get('position_x', 0), params.get('position_y', 0))
			o.obj_id = obj_id
			o.obj_type = obj_type
			o.obj_args = obj_args
			o.configure(params)
			#o.draw_ports()
			MFPGUI().remember(o)

	@rpcwrap
	def connect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
		MFPGUI().clutter_do(lambda: self._connect(obj_1_id, obj_1_port, obj_2_id, obj_2_port))

	def _connect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
		from .gui.connection_element import ConnectionElement

		obj_1 = MFPGUI().recall(obj_1_id)
		obj_2 = MFPGUI().recall(obj_2_id)
		c = ConnectionElement(MFPGUI().appwin, obj_1, obj_1_port, obj_2, obj_2_port)
		obj_1.connections_out.append(c)
		obj_2.connections_in.append(c)

	@rpcwrap
	def clear(self):
		pass

import cProfile

def profile(func):
    def wrapper(*args, **kwargs):
        datafn = func.__name__ + ".profile" # Name the data file sensibly
        prof = cProfile.Profile()
        retval = prof.runcall(func, *args, **kwargs)
        prof.dump_stats(datafn)
        return retval

    return wrapper

class MFPGUI (object):
	__metaclass__ = Singleton

	def __init__(self):
		self.objects = {}
		self.mfp = None 
		self.appwin = None
		self.clutter_thread = threading.Thread(target=self.clutter_proc)
		self.clutter_thread.start()

	def remember(self, obj):
		self.objects[obj.obj_id] = obj

	def recall(self, obj_id):
		return self.objects.get(obj_id)

	def clutter_do(self, thunk):
		from gi.repository import GObject
		GObject.idle_add(thunk, priority=GObject.PRIORITY_DEFAULT)

	def clutter_proc(self):
		from gi.repository import Clutter, GObject, Gtk, GtkClutter
		
		# explicit init seems to avoid strange thread sync/blocking issues 
		GObject.threads_init()
		Clutter.threads_init()
		GtkClutter.init([])

		# create main window
		from mfp.gui.patch_window import PatchWindow
		self.appwin = PatchWindow()	
		self.mfp = MFPCommand()

		# direct logging to GUI log console 
		log.log_func = self.appwin.log_write

		try:
			Gtk.main()
		except Exception, e:
			import traceback
			traceback.print_exc()

		# finish
		log.debug("MFPGUI.clutter_proc: clutter main has quit. finishing up")

	def finish(self):
		log.debug("MFPGUI.finish() called")
		if self.appwin:
			log.log_func = None 
			self.appwin.quit()
			self.appwin = None 

