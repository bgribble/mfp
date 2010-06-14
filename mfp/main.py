#! /usr/bin/env python2.6
'''
main.py: main routine for mfp

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import sys, os
import multiprocessing 

import mfp.dsp, mfp.gui
from mfp.duplex_queue import DuplexQueue, QRequest
from mfp import Bang 

class MFPApp (object):
	_instance = None 

	def __init__(self):
		# processor thread 
		self.dsp_queue = DuplexQueue()
		self.dsp_process = multiprocessing.Process(target=mfp.dsp.main,
												   args=(self.dsp_queue,)) 
		self.dsp_queue.init_requestor()
		
		# gui process connection
		self.gui_queue = DuplexQueue()
		self.gui_process = multiprocessing.Process(target=mfp.gui.main,
											       args=(self.gui_queue,))
		self.gui_queue.init_requestor(reader=self.gui_reader_thread)

		# processor class registry 
		self.registry = {} 
		
		# objects we give IDs to 
		self.objects = {}
		self.next_obj_id = 0 

		MFPApp._instance = self

		# start threads 
		self.dsp_process.start()
		self.gui_process.start()
		print "MFPApp: self=%s, dsp child=%s, gui child=%s" % (os.getpid(), self.dsp_process.pid, self.gui_process.pid)


	@classmethod
	def remember(klass, obj):
		oi = MFPApp._instance.next_obj_id
		MFPApp._instance.next_obj_id += 1
		MFPApp._instance.objects[oi] = obj
		return oi

	@classmethod 
	def recall(klass, obj_id):
		return MFPApp._instance.objects.get(obj_id)

	def gui_reader_thread(self):
		quit_req = False 
		while not quit_req:
			req = self.gui_queue.get()
			if not req:
				pass
			elif req.payload == 'quit':
				quit_req = True
			else:
				self.gui_command(req)
		print "GUI reader: got 'quit', exiting"
		MFPApp.finish()

	def gui_command(self, req):
		cmd = req.payload.get('cmd')
		args = req.payload.get('args')

		if cmd == 'create':
			strargs = args.get('args')
			if strargs is None:
				arglist = ()
			else:
				arglist = eval(strargs)
				if not isinstance(arglist, tuple):
					arglist = (arglist,)
			obj = MFPApp.create(args.get('type'), *arglist)
			obj_id = MFPApp.remember(obj)
			req.response = obj_id

		elif cmd == 'connect':
			obj_1 = MFPApp.recall(args.get('obj_1_id'))
			obj_2 = MFPApp.recall(args.get('obj_2_id'))

			r = obj_1.connect(args.get('obj_1_port'), obj_2, args.get('obj_2_port'))	
			req.response = r 

		self.gui_queue.put(req)

	@classmethod
	def register(klass, name, ctor):
		if MFPApp._instance is None:
			MFPApp._instance = MFPApp()
		print "MFPApp registering %s" % name 

		MFPApp._instance.registry[name] = ctor 

	@classmethod
	def dsp_message(klass, obj, callback=None):
		# print "MFPApp.dsp_message:", obj
		if MFPApp._instance is None:
			MFPApp._instance = MFPApp()
		req = QRequest(obj, callback=callback)
		MFPApp._instance.dsp_queue.put(req)
		return req 

	@classmethod 	
	def load(klass, filename):
		if MFPApp._instance is None:
			MFPApp._instance = MFPApp()
		pass

	@classmethod
	def create(klass, name, *args, **params):
		if MFPApp._instance is None:
			MFPApp._instance = MFPApp()
		ctor = MFPApp._instance.registry.get(name)
		if ctor is None:
			return False 
		else:
			print "create: ctor is", ctor 
			return ctor(*args, **params)

	@classmethod
	def wait(klass, req):
		MFPApp._instance.dsp_queue.wait(req)

	@classmethod
	def finish(klass):
		MFPApp.dsp_message("quit")
		MFPApp._instance.dsp_process.join()
		print "main thread reaped DSP process"
		MFPApp._instance.dsp_queue.finish()

import processors
import code 

def main():
	print "MFPAPP: pid=", os.getpid()
	m = MFPApp()
	processors.register()

	code.interact(local=locals())
	MFPApp.finish()



def testnetwork(): 
	import processors
	processors.register() 

	m = MFPApp.create("metro", 500)

	v = MFPApp.create("var", 0)
	plus = MFPApp.create("+", 1)
	mod = MFPApp.create("%", 4)

	# build the counter 
	m.connect(0, v, 0)
	v.connect(0, plus, 0)
	plus.connect(0, mod, 0)
	mod.connect(0, v, 1)

	# freq converter 
	r = MFPApp.create("route", 0, 1, 2, 3)
	f0 = MFPApp.create("var", 100)
	f1 = MFPApp.create("var", 200)
	f2 = MFPApp.create("var", 400)
	f3 = MFPApp.create("var", 800)
	
	v.connect(0, r, 0)
	r.connect(0, f0, 0)
	r.connect(1, f1, 0)
	r.connect(2, f2, 0)
	r.connect(3, f3, 0)

	# oscillator/dac 
	osc = MFPApp.create("osc~", 500)
	dac = MFPApp.create("dac~")
	
	f0.connect(0, osc, 0)
	f1.connect(0, osc, 0)
	f2.connect(0, osc, 0)
	f3.connect(0, osc, 0)
	
	osc.connect(0, dac, 0)
	m.send(True, 0)

	import code
	code.interact(local=locals())
	
	print "sending quit message"
	MFPApp.finish()



if __name__ == "__main__":
	main()
