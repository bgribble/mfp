

class PatchElement (object):
	'''
	Parent class of elements represented in the patch window 
	'''

	def __init__(self, window, x, y):
		self.actor = None 
		self.stage = window
		self.position_x = x
		self.position_y = y
		self.drag_x = None
		self.drag_y = None
		self.selected = False 
	
	def drag_start(self, x, y):
		self.drag_x = x - self.position_x
		self.drag_y = y - self.position_y

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		self.actor.set_position(x, y)

	def drag(self, x, y):
		self.move(x - self.drag_x, y - self.drag_y)

	def delete(self):
		self.stage.unregister(self.actor)
		self.actor.delete()
		self.actor = None

