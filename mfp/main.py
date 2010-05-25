#! /usr/bin/env python2.6
'''
main.py: main routine for mfp

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import sys
import multiprocessing 

import mfp.dsp

class MFPApp (object):
	_instance = None 
	def __init__(self):

		# gtk gui thread 
		self.dsp_read_queue = multiprocessing.Queue()
		self.dsp_write_queue = multiprocessing.Queue()
		self.dsp_process = multiprocessing.Process(target=mfp.dsp.main,
												   args=(self.dsp_read_queue, 
					                                     self.dsp_write_queue))

		# processor class registry 
		self.registry = {} 

		# start threads 
		self.dsp_process.start()

		MFPApp._instance = self 

	@classmethod
	def register(klass, name, ctor):
		MFPApp._instance.registry[name] = ctor 

	def dsp_message(self, obj):
		self.dsp_write_queue.put(obj)
	
	def load(self, filename):
		pass


def main(): 
	m = MFPApp()

	import mfp.processors
	d = mfp.processors.SPDac(0)
	o = mfp.processors.SPOsc(500)

	o.connect(0, d, 0)

	import code
	code.interact(local=locals())
	
	print "sending quit message"
	m.dsp_message('quit')



if __name__ == "__main__":
	main()
