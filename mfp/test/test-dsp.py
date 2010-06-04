
from unittest import TestCase

import mfpdsp
from mfp import processors
from mfp.main import MFPApp 


def setup():
	processors.register()


class DSPObjectTests (TestCase):
	_dsp_started = False 

	def test_create_destroy(self):
		'''test_create_destroy: can make a DSP object'''
		o = MFPApp.create("osc~", 500)

	def test_read(self):
		'''test_read: can read back a creation parameter'''
		o = MFPApp.create("osc~", 500)
		f = o.get_param("freq")
		print f 
		assert f == 500 

	def test_connect_disconnect(self):
		'''test_connect_disconnect: make/break connections'''
		inp = MFPApp.create("adc~", 0)
		outp = MFPApp.create("dac~", 0)

		inp.connect(0, outp, 0)
		inp.disconnect(0, outp, 0)


def teardown():
	MFPApp.finish()
	

