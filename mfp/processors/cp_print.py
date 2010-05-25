
from ..control_processor import ControlProcessor
from ..main import MFPApp

class CPPrint (ControlProcessor): 
	def __init__(self):
		ControlProcessor.__init__(self, inlets=1, outlets=0)
		MFPApp.register("print", CPPrint)

	def trigger(self):
		if self.inlets[0] is not None:
			print self.inlets[0]
			
