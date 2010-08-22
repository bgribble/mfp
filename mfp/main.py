#! /usr/bin/env python2.6
'''
main.py: main routine for mfp

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import sys, os
import multiprocessing 
import threading

import mfp.dsp_slave, mfp.gui_slave
from mfp.request_pipe import RequestPipe, Request
from mfp import Bang 
from patch import Patch

from singleton import Singleton

from rpc_wrapper import RPCWrapper, wrap
from rpc_worker import RPCWorker

def proc_monitor(process, quit_requested):
	process.join()
	if not quit_requested():
		print "PROCESS DIED UNEXPECTEDLY"

class MFPCommand(RPCWrapper):
	@wrap
	def create(objtype, initargs):
		obj = self.create(objtype, initargs)
		self.remember(obj)
		self.patch.add(obj)
		return obj.obj_id

	@wrap
	def connect(obj_1_id, obj_1_port, obj_2_id, obj_2_port):
		obj_1 = self.recall(obj_1_id)
		obj_2 = self.recall(obj_2_id)
		r = obj_1.connect(obj_1_port, obj_2, obj_2_port)	
		return r

	@wrap
	def  disconnect(obj_1_id, obj_1_port, obj_2_id, obj_2_port):
		obj_1 = self.recall(obj_1_id)
		obj_2 = self.recall(obj_2_id)

		r = obj_1.disconnect(obj_1_port, obj_2, obj_2_port)
		return r	

	@wrap
	def send_bang(obj_id, port):
		obj = self.recall(obj_id)
		obj.send(Bang, port)
		return True

	@wrap
	def delete(obj_id):
		obj = self.recall(obj_id)
		print "MFPApp: got delete req for", obj
		obj.delete()

	@wrap
	def gui_params(obj_id, params):
		obj = self.recall(args.get('obj_id'))
		obj.gui_params = params


class MFPApp (object):
	__metaclass__ = Singleton
	no_gui = False
	no_dsp = False

	def __init__(self):
		# processor thread 
		if not MFPApp.no_dsp:
			self.dsp_pipe = RequestPipe()
			self.dsp_process = multiprocessing.Process(target=mfp.dsp_slave.main,
													   args=(self.dsp_pipe,)) 
			self.dsp_quitreq = False
			checker = lambda: self.dsp_quitreq
			self.dsp_monitor = threading.Thread(target=proc_monitor, args=(self.dsp_process, checker))
			self.dsp_pipe.init_master()
		
		# gui process connection
		if not MFPApp.no_gui:
			self.gui_pipe = RequestPipe()
			self.gui_process = multiprocessing.Process(target=mfp.gui_slave.main,
													   args=(self.gui_pipe,))
			self.gui_pipe.init_master(reader=self.gui_reader_thread)

		# processor class registry 
		self.registry = {} 
		
		# objects we have given IDs to 
		self.objects = {}
		self.next_obj_id = 0 

		# while we only have 1 patch, this is it
		self.patch = Patch()

		# start threads 
		if not MFPApp.no_dsp:
			self.dsp_process.start()
			self.dsp_monitor.start()
		if not MFPApp.no_gui:
			self.gui_process.start()

	def remember(self, obj):
		oi = self.next_obj_id
		self.next_obj_id += 1
		self.objects[oi] = obj
		obj.obj_id = oi

		return oi

	def recall(self, obj_id):
		return self.objects.get(obj_id)

	def gui_reader_thread(self):
		quit_req = False 
		while not quit_req:
			req = self.gui_pipe.get()
			if not req:
				pass
			elif req.payload == 'quit':
				quit_req = True
			else:
				self.gui_command(req)
		print "GUI reader: got 'quit', exiting"
		self.finish()

	def register(self, name, ctor):
		print "MFPApp registering %s" % name 
		self.registry[name] = ctor 

	def dsp_message(self, obj, callback=None):
		print "self.dsp_message:", obj
		req = Request(obj, callback=callback)
		self.dsp_pipe.put(req)
		return req 

	def gui_message(self, obj, callback=None):
		# print "self.dsp_message:", obj
		req = Request(obj, callback=callback)
		self.gui_pipe.put(req)
		return req 

	def create(self, name, args=''):
		ctor = self.registry.get(name)
		if ctor is None:
			return None
		else:
			print "create: ctor is", ctor 
			obj = ctor(name, args)
			return obj

	def configure_gui(self, obj, params):
		msg = dict(cmd='configure')
		args = params.get('gui_params')
		# FIXME finish this

	def wait(self, req):
		self.dsp_pipe.wait(req)

	def finish(self):
		self.dsp_message("quit")
		self.dsp_quitreq = True
		self.dsp_monitor.join()
		print "main thread reaped DSP process"
		self.dsp_pipe.finish()


def main():
	import builtins 
	import code 

	m = MFPApp()
	builtins.register()

	def save(fn):
		m.patch.save_file(fn)

	def load(fn):
		m.patch.load_file(fn)

	code.interact(local=locals())

