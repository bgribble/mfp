#! /usr/bin/env python2.6
'''
gui.py
GTK/clutter gui for MFP -- main thread

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import threading 
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
	def finish(self):
		MFPGUI().appwin.destroy()

	@rpcwrap
	def create(self, obj_id, elementtype, params): 
		from .gtk.processor_element import ProcessorElement
		from .gtk.message_element import MessageElement
		from .gtk.text_element import TextElement

		ctors = {
			'processor': ProcessorElement,
			'message': MessageElement,
			'text': TextElement
		}
		ctor = ctors.get(elementtype)
		if ctor:
			o = ctor(MFPGUI().appwin, params.get('position_x', 0), params.get('position_y', 0))
			o.obj_id = obj_id
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
		print "MFPGUI: creating patch window"
		self.clutter_thread = threading.Thread(target=self.clutter_proc)
		self.clutter_thread.start()
		self.mfp = None 

	def clutter_proc(self):
		import clutter
		from mfp.gtk.patch_window import PatchWindow
		self.mfp = MFPCommand()
		self.appwin = PatchWindow()	
		clutter.main()

	def finish(self):
		self.appwin.destroy()

