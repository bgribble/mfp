#! /usr/bin/env python2.6
'''
main.py: main routine for mfp

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import sys
import multiprocessing 

import mfp.dsp
from mfp.duplex_queue import DuplexQueue, QRequest

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
		print "MFPApp.dsp_message:", obj
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
			return ctor(*args, **params)

	@classmethod
	def wait(klass, req):
		print "MFPApp: waiting for", req
		MFPApp._instance.dsp_queue.wait(req)
		print "MFPApp: done with wait for", req
		print "MFPApp: response =", req.response 

	@classmethod
	def finish(klass):
		MFPApp.dsp_message("quit")
		MFPApp._instance.dsp_queue.finish()

def main(): 
	import processors
	processors.register() 

	d = MFPApp.create("dac~")
	o = MFPApp.create("osc~", 500)
	o.connect(0, d, 0)

	import code
	code.interact(local=locals())
	
	print "sending quit message"
	m.dsp_message('quit')



if __name__ == "__main__":
	main()
