#! /usr/bin/env python
'''
main.py: main routine for mfp

Copyright (c) 2010-2012 Bill Gribble <grib@billgribble.com>
'''

import sys, os
import multiprocessing 
import threading
import time

from mfp.request_pipe import RequestPipe, Request
from mfp import Bang 
from patch import Patch
from scope import LexicalScope 
from singleton import Singleton
from interpreter import Interpreter 
from evaluator import Evaluator

from rpc_wrapper import RPCWrapper, rpcwrap
from rpc_worker import RPCServer

from . import log 

class MFPCommand(RPCWrapper):
	@rpcwrap
	def create(self, objtype, initargs, patch_name, scope_name, obj_name):
		patch = MFPApp().patches.get(patch_name)
		scope = patch.scopes.get(scope_name) or patch.default_scope

		obj = MFPApp().create(objtype, initargs, patch, scope, obj_name)
		if obj is None:
			log.debug("MFPApp.create: failed")
			return None
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
	def eval_and_send(self, obj_id, port, message):
		obj = MFPApp().recall(obj_id)
		obj.send(obj.parse_obj(message), port)
		return True

	@rpcwrap
	def delete(self, obj_id):
		obj = MFPApp().recall(obj_id)
		obj.patch.remove(obj)
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

	@rpcwrap
	def log_write(self, msg):
		MFPApp().gui_cmd.log_write(msg)

	@rpcwrap
	def console_eval(self, cmd):
		return MFPApp().console.runsource(cmd)

	@rpcwrap
	def quit(self):
		MFPApp().finish()

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

		self.console = None

		self.gui_cmd = None

		# processor class registry 
		self.registry = {} 
		
		# objects we have given IDs to 
		self.objects = {}
		self.next_obj_id = 0 
	
		# temporary name cache 
		self.objects_byname = {} 

		self.patches = {}

	def setup(self):
		from mfp.dsp_slave import dsp_init, DSPObject, DSPCommand 
		from mfp.gui_slave import gui_init, GUICommand

		RPCWrapper.node_id = "MFP Master"
		MFPCommand.local = True

		# dsp and gui processes
		if not MFPApp.no_dsp:
			num_inputs = 2
			num_outputs = 2
			self.dsp_process = RPCServer("mfp_dsp", dsp_init, num_inputs, num_outputs)
			self.dsp_process.serve(DSPObject)
			self.dsp_process.serve(DSPCommand)
			self.dsp_command = DSPCommand() 
		
		if not MFPApp.no_gui:
			self.gui_process = RPCServer("mfp_gui", gui_init)
			self.gui_process.serve(GUICommand)
			self.gui_cmd = GUICommand()
			while not self.gui_cmd.ready():
				time.sleep(0.2)
			log.debug("GUI is ready, switching logging to GUI")
			log.log_func = self.gui_cmd.log_write
			log.debug("Started logging to GUI")
			if self.dsp_command: 
				self.dsp_command.log_to_gui()

			self.console = Interpreter(self.gui_cmd.console_write, dict(app=self))
			self.gui_cmd.hud_write("<b>Welcome to MFP</b>")

		# midi manager 
		from . import midi
		self.midi_mgr = midi.MFPMidiManager(1, 1)
		self.midi_mgr.start()	
		log.debug("MIDI started (ALSA Sequencer)")

		# OSC manager 
		from . import osc 
		self.osc_mgr = osc.MFPOscManager(5555)
		self.osc_mgr.start()
		log.debug("OSC started on port 5555")

		# while we only have 1 patch, this is it
		self.patches["default"] = Patch('default', '')

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

	def create(self, init_type, init_args, patch, scope, name):
		ctor = self.registry.get(init_type)
		if ctor is None:
			log.debug("No factory for '%s' registered, cannot create" % init_type)
			return None
		else:
			try:
				obj = ctor(init_type, init_args, patch, scope, name)
				return obj
			except Exception, e:
				log.debug("Caught exception while trying to create %s (%s)" 
						  % (init_type, init_args))
				log.debug(e)
				raise

	def resolve(self, name, queryobj=None):
		'''
		Attempt to identify an object matching name

		If name has '.'-separated parts, use simple logic to treat
		parts as a path.  First match to the first element roots the
		search path; i.e. "foo.bar.baz" will match the first foo in
		the search path, and the first bar under that foo
		'''

		def find_part(part, base):
			if isinstance(base, (Patch, LexicalScope)):
				return base.resolve(part)
			return None

		parts = name.split('.')
		obj = None
		root = None 

		# first find the base 
		if queryobj and queryobj.patch:
			root = queryobj.patch.resolve(parts[0], queryobj.scope)
		if not root:
			for pname, pobj in self.patches.items():
				root = pobj.resolve(parts[0])
				
				if root:
					break 

		# now descend the path
		if root: 
			obj = root 
			for p in parts[1:]:
				obj = find_part(p, obj)
		return obj

	def finish(self):
		log.log_func = None 
		if self.console: 
			self.console.write_cb = None

		if self.dsp_process:
			log.debug("MFPApp.finish: reaping DSP slave...")
			self.dsp_process.finish()

		if self.gui_process:
			log.debug("MFPApp.finish: reaping GUI slave...")
			self.gui_process.finish()

		if self.midi_mgr: 
			log.debug("MFPApp.finish: reaping MIDI thread...")
			self.midi_mgr.finish()

		if self.osc_mgr:
			log.debug("MFPApp.finish: reaping OSC thread...")
			self.osc_mgr.finish()

		log.debug("MFPApp.finish: all children reaped, good-bye!")

def main():
	import math, os, sys, re 
	from mfp import builtins

	log.debug("Main thread started, pid =", os.getpid())
	#log.log_file = open("mfp.log", "w+")

	app = MFPApp()
	app.setup()

	# default names known to the evaluator 
	Evaluator.bind_global("math", math)
	Evaluator.bind_global("os", os)
	Evaluator.bind_global("sys", sys)
	Evaluator.bind_global("re", sys)

	from mfp.bang import Bang, Uninit 
	from mfp.method import MethodCall 
	Evaluator.bind_global("Bang", Bang)
	Evaluator.bind_global("Uninit", Uninit)
	Evaluator.bind_global("MethodCall", MethodCall)

	from mfp.midi import NoteOn, NoteOff 
	Evaluator.bind_global("NoteOn", NoteOn)
	Evaluator.bind_global("NoteOff", NoteOff)
	
	Evaluator.bind_global("builtins", builtins)
	Evaluator.bind_global("app", app)

	builtins.register()
	log.debug("main: builtins registered")
	
	if len(sys.argv) > 1:
		log.debug("main: loading", sys.argv[1])
		app.patches.get("default").load_file(sys.argv[1])

