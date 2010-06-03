#! /usr/bin/env python2.6
'''
main.py: main routine for mfp

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import sys
import multiprocessing 

import mfp.dsp
from mfp.duplex_queue import DuplexQueue

class MFPApp (object):
	
	_instance = None 

	def __init__(self):

		# gtk gui thread 
		self.dsp_queue = DuplexQueue()
		self.dsp_process = multiprocessing.Process(target=mfp.dsp.main,
												   args=(self.dsp_queue,)) 

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
	def dsp_message(klass, obj):
		print "MFPApp.dsp_message:", obj
		if MFPApp._instance is None:
			MFPApp._instance = MFPApp()
		req = QRequest(obj)
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
