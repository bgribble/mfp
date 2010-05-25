#! /usr/bin/env python2.6 
'''
dsp.py
Python main loop for DSP subprocess 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
import mfpdsp

class MFPDSP (object):
	def __init__(self, read_queue, write_queue):
		self.read_queue = read_queue
		self.write_queue = write_queue
		
	def start (self):
		# start JACK thread 
		mfpdsp.dsp_startup(1, 1)

		time_to_quit = False

		while not time_to_quit:
			qcmd = self.read_queue.get()
			print "got queue data"
			print qcmd

			if qcmd == 'quit':
				time_to_quit = True

		return True

def main(write_q, read_q):
	dspapp = MFPDSP(read_q, write_q)
	dspapp.start()

