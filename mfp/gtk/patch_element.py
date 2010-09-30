
from mfp import MFPGUI 

class PatchElement (object):
	'''
	Parent class of elements represented in the patch window 
	'''

	def __init__(self, window, x, y):
		self.obj_id = None
		self.obj_type = None
		self.obj_args = None
		self.num_inlets = 0
		self.num_outlets = 0
		self.dsp_inlets = []
		self.dsp_outlets = []

		self.actor = None 
		self.stage = window
		self.position_x = x
		self.position_y = y
		self.drag_x = None
		self.drag_y = None
		self.selected = False 

		self.edit_mode = None
		self.control_mode = None

	def drag_start(self, x, y):
		self.drag_x = x - self.position_x
		self.drag_y = y - self.position_y

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		self.actor.set_position(x, y)

	def drag(self, x, y):
		self.move(x - self.drag_x, y - self.drag_y)

	def begin_edit(self):
		pass

	def delete(self):
		self.stage.unregister(self)
		self.actor = None
		if self.obj_id is not None:
			MFPGUI().mfp.delete(self.obj_id)
			self.obj_id = None

	def send_params(self, **extras):
		prms = dict(position_x=self.position_x, position_y=self.position_y, 
					element_type=self.element_type)
		for k, v in extras.items():
			prms[k] = v
		if self.obj_id is not None:
			MFPGUI().mfp.set_params(self.obj_id, prms)

	def configure(self, params):
		self.num_inlets = params.get("num_inlets")
		self.num_outlets = params.get("num_outlets")
		self.dsp_inlets = params.get("dsp_inlets")
		self.dsp_outlets = params.get("dsp_outlets")

	def make_edit_mode(self):
		return None

	def make_control_mode(self):
		return None

	def begin_edit(self):
		if not self.edit_mode:
			self.edit_mode = self.make_edit_mode()

		if self.edit_mode:
			self.stage.input_mgr.enable_minor_mode(self.edit_mode)

	def end_edit(self):
		if self.edit_mode:
			self.stage.input_mgr.disable_minor_mode(self.edit_mode)
			self.edit_mode = None

	def begin_control(self):
		if not self.control_mode:
			self.control_mode = self.make_control_mode()

		if self.control_mode:
			self.stage.input_mgr.enable_minor_mode(self.control_mode)
		
	def end_control(self):
		if self.control_mode:
			self.stage.input_mgr.disable_minor_mode(self.control_mode)
			self.control_mode = None

