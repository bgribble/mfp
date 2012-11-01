#! /usr/bin/env python2.7
'''
main.py: main routine for mfp

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import sys, os
import multiprocessing 
import threading
import time

from mfp.request_pipe import RequestPipe, Request
from mfp import Bang 
from patch import Patch

from singleton import Singleton

from rpc_wrapper import RPCWrapper, rpcwrap
from rpc_worker import RPCServer

from . import log 

class MFPCommand(RPCWrapper):
	@rpcwrap
	def create(self, objtype, initargs=''):
		obj = MFPApp().create(objtype, initargs)
		if obj is None:
			log.debug("MFPApp.create() failed")
			return None
		MFPApp().patch.add(obj)
		return obj.gui_params

	@rpcwrap
	def connect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
		obj_1 = MFPApp().recall(obj_1_id)
		obj_2 = MFPApp().recall(obj_2_id)
		r = obj_1.connect(obj_1_port, obj_2, obj_2_port)	
		return r

	@rpcwrap
	def disconnect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
		obj_1 = MFPApp().recall(obj_1_id)
		obj_2 = MFPApp().recall(obj_2_id)

		r = obj_1.disconnect(obj_1_port, obj_2, obj_2_port)
		return r	

	@rpcwrap
	def send_bang(self, obj_id, port):
		obj = MFPApp().recall(obj_id)
		obj.send(Bang, port)
		return True

	@rpcwrap
	def send(self, obj_id, port, data):
		obj = MFPApp().recall(obj_id)
		obj.send(data, port)
		return True

	@rpcwrap
	def delete(self, obj_id):
		obj = MFPApp().recall(obj_id)
		obj.delete()

	@rpcwrap
	def set_params(self, obj_id, params):
		obj = MFPApp().recall(obj_id)
		obj.gui_params = params

	@rpcwrap
	def get_info(self, obj_id):
		obj = MFPApp().recall(obj_id)
		return dict(num_inlets=len(obj.inlets), 
			        num_outlets=len(obj.outlets),
			        dsp_inlets=obj.dsp_inlets,
			        dsp_outlets=obj.dsp_outlets)

class MFPApp (object):
	__metaclass__ = Singleton
	no_gui = False
	no_dsp = False

	def __init__(self):
		self.dsp_process = None
		self.gui_process = None

		# threads in this process 
		self.midi_mgr = None 
		self.osc_mgr = None 

		self.gui_cmd = None

		# processor class registry 
		self.registry = {} 
		
		# objects we have given IDs to 
		self.objects = {}
		self.next_obj_id = 0 
	
		self.patch = None	

	def setup(self):
		import os
		log.debug("MFPApp: setup, pid =", os.getpid())

		from mfp.dsp_slave import dsp_init, DSPObject
		from mfp.gui_slave import gui_init, GUICommand

		RPCWrapper.node_id = "MFP Master"
		MFPCommand.local = True

		# dsp and gui processes
		if not MFPApp.no_dsp:
			num_inputs = 2
			num_outputs = 2
			self.dsp_process = RPCServer("mfp_dsp", dsp_init, num_inputs, num_outputs)
			self.dsp_process.serve(DSPObject)
		
		if not MFPApp.no_gui:
			self.gui_process = RPCServer("mfp_gui", gui_init)
			self.gui_process.serve(GUICommand)
			self.gui_cmd = GUICommand()
			while not self.gui_cmd.ready():
				time.sleep(0.2)
			log.debug("MFPApp: GUI is ready")

		# midi manager 
		from . import midi
		self.midi_mgr = midi.MFPMidiManager(1, 1)
		self.midi_mgr.start()	
		log.debug("MFPMidiManager started")

		# OSC manager 
		# from . import osc 
		# self.osc_manager = osc.MFPOscManager(5555)
		# self.osc_manager.start()

		# while we only have 1 patch, this is it
		self.patch = Patch('default', '')

	def remember(self, obj):
		oi = self.next_obj_id
		self.next_obj_id += 1
		self.objects[oi] = obj
		obj.obj_id = oi

		return oi

	def recall(self, obj_id):
		return self.objects.get(obj_id)

	def register(self, name, ctor):
		self.registry[name] = ctor 

	def create(self, name, args=''):
		ctor = self.registry.get(name)
		if ctor is None:
			return None
		else:
			obj = ctor(name, args)
			return obj

	def finish(self):
		if self.dsp_process:
			self.dsp_process.finish()
		if self.gui_process:
			self.gui_process.finish()

def main():
	import os
	import builtins 
	import code 
	import sys

	log.debug("MFP.main, pid =", os.getpid())

	m = MFPApp()

	log.debug("MFPApp created")

	m.setup()
	
	log.debug("MFPApp configured")

	builtins.register()

	log.debug("MFPApp builtins registered")

	if len(sys.argv) > 1:
		log.debug("loading", sys.argv[1])
		m.patch.load_file(sys.argv[1])
	
	code.interact(local=locals())
	m.finish()
