#! /usr/bin/env python2.6
'''
main.py: main routine for mfp

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import sys
import multiprocessing 

import dsp

class MFPApp (object):
	def __init__(self):

		# gtk gui thread 
		self.dsp_read_queue = multiprocessing.Queue()
		self.dsp_write_queue = multiprocessing.Queue()
		self.dsp_process = multiprocessing.Process(target=dsp.main,
												   args=(self.dsp_read_queue, 
					                                     self.dsp_write_queue))
		# start threads 
		self.dsp_process.start()
		
	def dsp_message(self, obj):
		self.dsp_write_queue.put(obj)
	
	def load(self, filename):
		pass



if __name__ == "__main__":
	mfp = MFPApp()

	print "sleeping for 10 secs"
	import time
	time.sleep(10)

	print "sending quit message"
	mfp.dsp_message('quit')



