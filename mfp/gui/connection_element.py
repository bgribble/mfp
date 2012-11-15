
from patch_element import PatchElement
from gi.repository import Clutter 
import math 
from mfp import MFPGUI, log

class ConnectionElement(PatchElement):
	ELBOW_ROOM = 2
	def __init__(self, window, obj_1, port_1, obj_2, port_2):
		PatchElement.__init__(self, window, obj_1.position_x, obj_1.position_y)
		
		self.texture = Clutter.CairoTexture.new(10,10)
		self.obj_1 = obj_1
		self.port_1 = port_1
		self.obj_2 = obj_2
		self.port_2 = port_2
		self.swapends = 0
		self.width = None  
		self.height = None 

		self.texture.connect("draw", self.draw_cb)
		self.add_actor(self.texture)
		self.draw()

	def select(self):
		self.selected = True 
		self.draw()

	def unselect(self):
		self.selected = False 
		self.draw()

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
	
		self.swapends = False 
		if (p1[0] > p2[0]):
			self.swapends = not self.swapends
		if (p1[1] > p2[1]):
			self.swapends = not self.swapends

		self.position_x = min(p1[0], p2[0]) - self.ELBOW_ROOM
		self.position_y = min(p1[1], p2[1]) - self.ELBOW_ROOM
		self.width = abs(p2[0] - p1[0]) + 2*self.ELBOW_ROOM 
		self.height = abs(p2[1] - p1[1]) + 2*self.ELBOW_ROOM 

		self.set_position(self.position_x, self.position_y)
		self.texture.set_position(0,0)
		self.texture.set_size(self.width, self.height)
		self.texture.set_surface_size(self.width, self.height)
		self.texture.invalidate()

	def draw_cb(self, texture, ctx):
		if self.selected: 
			c = self.stage.color_selected
		else:
			c = self.stage.color_unselected
		texture.clear()
		ctx.set_source_rgba(c.red, c.green, c.blue, 1.0)
		ctx.set_line_width(1.25)
		if self.swapends:
			ctx.move_to(self.ELBOW_ROOM, self.height-self.ELBOW_ROOM)
			ctx.line_to(self.width-self.ELBOW_ROOM, self.ELBOW_ROOM)
		else:
			ctx.move_to(self.ELBOW_ROOM, self.ELBOW_ROOM)
			ctx.line_to(self.width-self.ELBOW_ROOM, self.height-self.ELBOW_ROOM)
		ctx.close_path()
		ctx.stroke()


