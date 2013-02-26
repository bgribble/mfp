
from unittest import TestCase
from mfp.patch import Patch
from mfp.main import MFPApp

import simplejson as json

def mkproc(case, init_type, init_args=None):
    return MFPApp().create(init_type, init_args, case.patch, None, init_type)


class PatchTests (TestCase):
    def setUp(self):
        MFPApp().no_gui = True
        MFPApp().next_obj_id = 0
        MFPApp().objects = {}
        self.patch = Patch('default', '', None, None, 'default')
        pass

    def test_loadsave(self):
        o1 = mkproc(self, "message", "'hello, world'")
        o2 = mkproc(self, "print")
        o1.connect(0, o2, 0)
        json_1 = self.patch.json_serialize()
        self.patch.delete()

        MFPApp().next_obj_id = 0 
        p2 = Patch('default', '', None, None, 'default')
        p2.json_deserialize(json_1)

        json_2 = p2.json_serialize()

        dict_1 = json.loads(json_1)
        dict_2 = json.loads(json_2)
        fail = False 

        for elt in [ 'gui_params', 'objects', 'type', 'scopes' ]:
            if dict_1.get(elt) != dict_2.get(elt):
                print "=======", elt, "========"
                print dict_1.get(elt)
                print "====================="
                print dict_2.get(elt)
                fail = True 

        self.assertEqual(fail, False)

    def test_inlet_outlet (self):
        o1 = mkproc(self, "inlet")
        o2 = mkproc(self, "outlet")
        o1.connect(0, o2, 0)
        
        p2 = Patch('default', '', None, None, 'default')
        o3 = MFPApp().create("inlet", None, p2, None, "inlet")
        o4 = MFPApp().create("outlet", None, p2, None, "outlet")
        o3.connect(0, o4, 0)

        self.patch.connect(0, p2, 0)
        self.patch.send(True)

        self.assertEqual(p2.outlets[0], True)

        

