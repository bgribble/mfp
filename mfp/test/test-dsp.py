
from unittest import TestCase

import mfpdsp
import mfp 
from mfp.main import MFPApp 

class DSPObjectTests (TestCase):
	def test_create(self):
		'''test_create: [dsp] can make a DSP object'''
		o = MFPApp().create("osc~", "500")

	def test_read(self):
		'''test_read: [dsp] can read back a creation parameter'''
		o = MFPApp().create("osc~", "500")
		print "test_read: objid = ", o, o.dsp_obj
		f = o.dsp_getparam("freq")
		print f 
		assert f == 500 

	def test_connect_disconnect(self):
		'''test_connect_disconnect: [dsp] make/break connections'''
		inp = MFPApp().create("adc~", "0")
		outp = MFPApp().create("dac~", "0")

		inp.connect(0, outp, 0)
		inp.disconnect(0, outp, 0)

	def test_delete(self):
		'''test_destroy: [dsp] destroy dsp object'''
		inp = MFPApp().create("adc~", "0")
		outp = MFPApp().create("dac~", "0")

		inp.connect(0, outp, 0)
		outp.delete()
		inp.delete()
		
def teardown():
	MFPApp().finish()
	

