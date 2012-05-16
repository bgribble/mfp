
from patch_element import PatchElement
from gi.repository import Clutter as clutter 
import math 
from mfp import MFPGUI

class ConnectionElement(PatchElement):
	def __init__(self, window, obj_1, port_1, obj_2, port_2):
		PatchElement.__init__(self, window, obj_1.position_x, obj_1.position_y)
		
		self.actor = clutter.Rectangle()
		self.obj_1 = obj_1
		self.port_1 = port_1
		self.obj_2 = obj_2
		self.port_2 = port_2
		self.rotation = 0
		self.width = None  
		self.height = None 
		
		self.actor.set_color(window.color_unselected)
		self.stage.register(self)
		self.draw()

	def select(self):
		self.selected = True 
		self.actor.set_color(self.stage.color_selected)

	def unselect(self):
		self.selected = False 
		self.actor.set_color(self.stage.color_unselected)

	def delete(self):
		MFPGUI().mfp.disconnect(self.obj_1.obj_id, self.port_1, self.obj_2.obj_id, self.port_2)
		self.obj_1.connections_out.remove(self)
		self.obj_2.connections_in.remove(self)
		self.obj_1 = None
		self.obj_2 = None
		PatchElement.delete(self)

	def draw(self):
		p1 = self.obj_1.port_center(PatchElement.PORT_OUT, self.port_1)
		p2 = self.obj_2.port_center(PatchElement.PORT_IN, self.port_2)
		
		self.position_x = p1[0]
		self.position_y = p1[1]
		self.width = 1.5 
		self.height = ((p2[0]-p1[0])**2 + (p2[1] - p1[1])**2)**0.5
		self.rotation = math.atan2(p1[0] - p2[0], p2[1]-p1[1]) * 180.0 / math.pi

		self.actor.set_size(self.width, self.height)
		self.actor.set_position(self.position_x, self.position_y)
		self.actor.set_rotation(clutter.RotateAxis.Z_AXIS, self.rotation, 0, 0, 0)

