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

def gui_init(pipe):
	import os
	print "gui_init: in worker, pid =", os.getpid()
	pipe.on_finish(gui_finish)
	RPCWrapper.pipe = pipe
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
	def finish(self):
		MFPGUI().appwin.destroy()

	@rpcwrap
	def configure(self, obj_id, params):
		print "GuiCommand:", obj_id, params
		MFPGUI().clutter_do(lambda: self._configure(obj_id, params))
		#MFPGUI().clutter_do(lambda: True)
		print "Guicommand done"
		return True

	def _configure(self, obj_id, params):
		print "_configure: enter"
		obj = MFPGUI().recall(obj_id)
		print "_configure:", obj_id, obj
		obj.configure(params)

	@rpcwrap
	def create(self, obj_type, obj_args, obj_id, params): 
		MFPGUI().clutter_do(lambda: self._create(obj_type, obj_args, obj_id, params))

	def _create(self, obj_type, obj_args, obj_id, params): 
		from .gtk.processor_element import ProcessorElement
		from .gtk.message_element import MessageElement
		from .gtk.text_element import TextElement
		from .gtk.enum_element import EnumElement
		
		elementtype = params.get('element_type')
		print "Create:", obj_id, elementtype, params
		print "mfpgui:", MFPGUI(), MFPGUI().appwin

		ctors = {
			'processor': ProcessorElement,
			'message': MessageElement,
			'text': TextElement,
			'enum': EnumElement
		}
		ctor = ctors.get(elementtype)
		if ctor:
			o = ctor(MFPGUI().appwin, params.get('position_x', 0), params.get('position_y', 0))
			o.obj_id = obj_id
			o.obj_type = obj_type
			o.obj_args = obj_args
			o.configure(params)
			MFPGUI().remember(o)

	@rpcwrap
	def connect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
		MFPGUI().clutter_do(lambda: self._connect(obj_1_id, obj_1_port, obj_2_id, obj_2_port))

	def _connect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
		from .gtk.connection_element import ConnectionElement

		obj_1 = MFPGUI().recall(obj_1_id)
		obj_2 = MFPGUI().recall(obj_2_id)
		print "MFPGUI._connect:", obj_1_id, obj_1, obj_2_id, obj_2
		print MFPGUI().objects
		c = ConnectionElement(MFPGUI().appwin, obj_1, obj_1_port, obj_2, obj_2_port)
		obj_1.connections_out.append(c)
		obj_2.connections_in.append(c)

	@rpcwrap
	def clear(self):
		pass

class MFPGUI (object):
	__metaclass__ = Singleton

	def __init__(self):
		self.clutter_thread = threading.Thread(target=self.clutter_proc)
		self.clutter_thread.start()
		self.objects = {}
		self.mfp = None 
		self.appwin = None

	def remember(self, obj):
		self.objects[obj.obj_id] = obj

	def recall(self, obj_id):
		return self.objects.get(obj_id)

	def clutter_do(self, thunk):
		import glib
		print "clutter_do: adding", thunk
		glib.idle_add(thunk)

	def clutter_proc(self):
		import clutter
		import glib
		
		# explicit init seems to avoid strange thread sync/blocking issues 
		glib.threads_init()
		clutter.threads_init()
		clutter.init()

		# create main window
		from mfp.gtk.patch_window import PatchWindow
		self.appwin = PatchWindow()	
		self.mfp = MFPCommand()
		clutter.main()

	def finish(self):
		self.appwin.destroy()

