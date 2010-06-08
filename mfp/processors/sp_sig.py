#! /usr/bin/env python2.6
'''
sp_sig.py:  Builtin constant signal 
'''

from mfp.signal_processor import SignalProcessor 
from mfp.control_processor import ControlProcessor
from mfp.main import MFPApp

class SPSig(SignalProcessor, ControlProcessor):
	def __init__(self, *initargs):
		if len(initargs):
			value = initargs[0]
		else:
			value = 0

		SignalProcessor.__init__(self, "sig~", 0, 1, value=value)
		ControlProcessor.__init__(self, 1, 0)

	def connect(self, outlet, target, inlet):
		return SignalProcessor.connect(self, outlet, target, inlet)

	def disconnect(self, outlet, target, inlet):
		return SignalProcessor.disconnect(self, outlet, target, inlet)

	def trigger(self):
		try:
			val = float(self.inlets[0])
			self.set_param("value", val)
		except:
			print "Can't convert %s to a value" % self.inlet[0]
				

def register():
	MFPApp.register("sig~", SPSig)

