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
	def create(self, obj_type, obj_args, obj_id, params): 
		MFPGUI.clutter_do(lambda: self._create(obj_type, obj_args, obj_id, params))

	def _create(self, obj_type, obj_args, obj_id, params): 
		from .gtk.processor_element import ProcessorElement
		from .gtk.message_element import MessageElement
		from .gtk.text_element import TextElement
		
		elementtype = params.get('element_type')
		print "Create:", obj_id, elementtype, params
		print "mfpgui:", MFPGUI(), MFPGUI().appwin

		ctors = {
			'processor': ProcessorElement,
			'message': MessageElement,
			'text': TextElement
		}
		ctor = ctors.get(elementtype)
		if ctor:
			o = ctor(MFPGUI().appwin, params.get('position_x', 0), params.get('position_y', 0))
			o.obj_id = obj_id
			o.obj_type = obj_type
			o.obj_args = obj_args
			o.configure(params)

	@rpcwrap
	def connect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
		pass

	@rpcwrap
	def clear(self):
		pass

class MFPGUI (object):
	__metaclass__ = Singleton

	def __init__(self):
		print "MFPGUI: creating patch window in", os.getpid()
		print "self:", self
		import time
		self.clutter_thread = threading.Thread(target=self.clutter_proc)
		self.clutter_thread.start()
		self.mfp = None 
		self.appwin = None

	def clutter_do(self, thunk):
		import glib
		glib.idle_add(thunk)

	def clutter_proc(self):
		print "clutter main thread starting"
		import clutter
		from mfp.gtk.patch_window import PatchWindow
		self.appwin = PatchWindow()	
		print "created patchwindow", self.appwin
		self.mfp = MFPCommand()
		clutter.main()

	def finish(self):
		self.appwin.destroy()

