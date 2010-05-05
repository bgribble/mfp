
from control_processor import ControlProcessor

class CPPrint (ControlProcessor): 
	def __init__(self):
		ControlProcessor.__init__(self, inlets=1, outlets=0)

	def trigger(self):
		if self.inlets[0] is not None:
			print self.inlets[0]
			
