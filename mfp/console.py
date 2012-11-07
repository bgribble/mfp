#! /usr/bin/env python
'''
console.py -- Python read-eval-print console for MFP 

Copyright (c) 2012 Bill Gribble <grib@billgribble.com> 
'''

from threading import Thread 
import code 
import sys 
import select 
from mfp import log 

class Console (Thread):
	def __init__ (self, local={}):
		self.local = local
		self.console = code.InteractiveConsole(self.local) 
		self.in_fd = sys.stdin 
		self.out_fd = sys.stdout 

		self.quitreq = False 
		sys.ps1 = '>>> '
		sys.ps2 = '... '
		Thread.__init__(self)

	def run(self):
		log.debug("console: starting REPL, 'app' is MFP application") 	
		continued = False 
		while not self.quitreq:
			# write the line prompt 
			if not continued: 
				self.console.write(sys.ps1)
			else:
				self.console.write(sys.ps2)

			# wait for input, possibly quitting if needed 
			input_ready = False 
			while not input_ready and not self.quitreq:
				r, _, _ = select.select([sys.stdin], [], [], .2)	
				if sys.stdin in r: 
					input_ready = True 

			if input_ready:
				cmd = sys.stdin.readline()
				#log.debug("Got input:", cmd)
				continued = self.console.push(cmd)
		log.debug("REPL thread got quit") 

	def finish(self):
		self.quitreq = True 
		self.join()

