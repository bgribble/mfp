#! /usr/bin/env python2.6
'''
main.py: main routine for mfp

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import sys
import multiprocessing 

import mfp.dsp
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

		# processor class registry 
		self.registry = {} 
		
		# start threads 
		self.dsp_process.start()

		MFPApp._instance = self 

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
		MFPApp._instance.dsp_queue.finish()

def main(): 
	import processors
	processors.register() 

	m = MFPApp.create("metro", 250)

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
