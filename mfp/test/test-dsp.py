
from unittest import TestCase

import mfpdsp
import mfp 
from mfp.main import MFPApp 
from mfp.patch import Patch

def setup():
	MFPApp().setup()
	from mfp.dsp_slave import DSPObject
	print "DSPObject pipe:", DSPObject.pipe

def mkproc(case, init_type, init_args=None):
	return MFPApp().create(init_type, init_args, case.patch, None, init_type) 

class DSPObjectTests (TestCase):
	def setUp(self):
		self.patch = Patch('default', '', None, None, 'default')

	def tearDown(self):
		import time
		time.sleep(0.500)

	def test_create(self):
		'''test_create: [dsp] can make a DSP object'''
		o = mkproc(self, "osc~", "500")

	def test_read(self):
		'''test_read: [dsp] can read back a creation parameter'''
		o = mkproc(self, "osc~", "500")
		print "test_read: objid = ", o, o.dsp_obj
		f = o.dsp_obj.getparam("_sig_1")
		print f 
		assert f == 500 

	def test_connect_disconnect(self):
		'''test_connect_disconnect: [dsp] make/break connections'''
		print "============= Creating in~"
		inp = mkproc(self, "in~", "0")
		print "============= Creating out~"
		outp = mkproc(self, "out~", "0")
		
		print "============= Created objects"
		inp.connect(0, outp, 0)
		print "============= Called connect"
		inp.disconnect(0, outp, 0)
		print "============== disconnected"

	def test_delete(self):
		'''test_destroy: [dsp] destroy dsp object'''
		print "Creating"
		inp = mkproc(self, "in~", "0")
		outp = mkproc(self, "out~", "0")
		print "connecting"
		inp.connect(0, outp, 0)
		print "deleting"
		outp.delete()
		inp.delete()
		print "done"
		
def teardown():
	MFPApp().finish()
	print "test-dsp.py: MFPApp finish done"	

