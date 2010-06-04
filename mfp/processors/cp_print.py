
from ..control_processor import ControlProcessor
from ..main import MFPApp

class CPPrint (ControlProcessor): 
	def __init__(self, fmt_string="%s"):
		self.format_string = fmt_string 
		ControlProcessor.__init__(self, inlets=2, outlets=1)

	def trigger(self):
		if self.inlets[1] is not None:
			self.format_string = self.inlets[1]

		if self.inlets[0] is not None:
			out = self.format_string % self.inlets[0]
			self.outlets[0] = out 
			print out 

		self.propagate()
			
def register():
	MFPApp.register("print", CPPrint)
