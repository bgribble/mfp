
from patch_element import PatchElement
import clutter 
import math 
from mfp import MFPGUI

class Point(object):
	def __init__(self, x, y):
		self.x = x
		self.y = y

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

	def output_pos(self, obj, port):
		h = obj.actor.get_height()
		dx = 5 + port*5
		return Point(obj.position_x + dx, obj.position_y + h)

	def input_pos(self, obj, port):
		dx = 5 + port*5
		return Point(obj.position_x + dx, obj.position_y)

	def select(self):
		self.selected = True 
		self.actor.set_color(self.stage.color_selected)

	def unselect(self):
		self.selected = False 
		self.actor.set_color(self.stage.color_unselected)

	def delete(self):
		MFPGUI.mfp.disconnect(self.obj_1.obj_id, self.port_1, self.obj_2.obj_id, self.port_2)
		self.obj_1.connections_out.remove(self)
		self.obj_2.connections_in.remove(self)
		self.obj_1 = None
		self.obj_2 = None
		PatchElement.delete(self)

	def draw(self):
		p1 = self.output_pos(self.obj_1, self.port_1)
		p2 = self.input_pos(self.obj_2, self.port_2)
		
		self.position_x = p1.x
		self.position_y = p1.y 
		self.width = 1.5 
		self.height = ((p2.x-p1.x)**2 + (p2.y - p1.y)**2)**0.5
		self.rotation = math.atan2(p1.x - p2.x, p2.y-p1.y) * 180.0 / math.pi

		self.actor.set_size(self.width, self.height)
		self.actor.set_position(self.position_x, self.position_y)
		self.actor.set_rotation(clutter.Z_AXIS, self.rotation, 0, 0, 0)

