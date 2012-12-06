
from unittest import TestCase
from mfp.patch import Patch
from mfp.main import MFPApp

import simplejson as json

jsdata_1 = '''
{"objects": {
"1": {"connections": [[]], "initargs": "True", "type": "var", 
	"gui_params": {"element_type": "message", "position_x": 118.0, "position_y": 423.0}}, 
"2": {"connections": [[]], "initargs": "False", "type": "var", 
	"gui_params": {"element_type": "message", "position_x": 204.0, "position_y": 424.0}}, 
"3": {"connections": [[]], "initargs": "0", "type": "var", 
	"gui_params": {"element_type": "enum", "position_x": 327.0, "position_y": 263.0}}, 
"4": {"connections": [[]], "initargs": "", "type": "var", 
	"gui_params": {"message_text": "HIGH", "element_type": "text", "position_x": 386.0, "position_y": 162.0}}, 
"5": {"connections": [[]], "initargs": "", "type": "var", 
	"gui_params": {"message_text": "LOW", "element_type": "text", "position_x": 389.0, "position_y": 363.0}}, 
"6": {"connections": [[]], "initargs": "", "type": "var", 
	"gui_params": {"message_text": "test-enum-gui.mfp", "element_type": "text", "position_x": 22.0, "position_y": 28.0}}}, 
"type": "default"}
'''
jsdata_2 = '''
{"objects": {
"1": {"connections": [[[2, 0]]], "initargs": null, "type": "inlet", 
      "gui_params": {"element_type": "processor", "position_x": 88.0, "position_y": 55.0}}, 
"2": {"connections": [[]], "initargs": null, "type": "outlet", 
      "gui_params": {"element_type": "processor", "position_x": 88.0, "position_y": 136.0}}}, 
"type": "default"}
'''

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
		self.patch.json_deserialize(jsdata_1)
		o1 = json.loads(jsdata_1)
		o2 = json.loads(self.patch.json_serialize())
		self.assertEqual(len(o1), len(o2))
		obj1 = o1.get('objects')
		obj2 = o2.get('objects')
		for k in obj1:
			print k
			print obj1.get(k)
			print obj2.get(k)
			self.assertEqual(obj1.get(k), obj2.get(k))
		self.assertEqual(o1, o2)

	def test_inout(self):
		self.patch.json_deserialize(jsdata_2)
		
		v = mkproc(self, "var")
		self.patch.connect(0, v, 0)
		self.patch.send(True)

		self.assertEqual(v.outlets[0], True)
