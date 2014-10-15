
from unittest import TestCase
from mfp.patch import Patch
from ..mfp_app import MFPApp
from mfp.scope import NaiveScope


def mkproc(case, init_type, init_args=None):
    return MFPApp().create(init_type, init_args, case.patch, None, init_type)

class DSPErrorTests (TestCase):
    def setUp(self):
        MFPApp().setup()
        MFPApp().no_gui = True
        MFPApp().no_restart = True 
        MFPApp().next_obj_id = 0
        MFPApp().objects = {}
        self.patch = Patch('default', '', None, NaiveScope(), 'default')
        self.errtest = mkproc(self, "errtest~")
        pass

    def test_configerr(self):
        self.errtest.dsp_obj.setparam("err_config", 1.0)
        import time
        time.sleep(1)
        
    def test_processerr(self):
        self.errtest.dsp_obj.setparam("err_process", 1.0)
        import time
        time.sleep(1)
        
    def test_deleteerr(self):
        self.errtest.dsp_obj.setparam("err_delete", 1.0)
        self.errtest.delete()
        import time 
        time.sleep(1)
    
    def tearDown(self):
        MFPApp().finish()
        

