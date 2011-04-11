
from ..processor import Processor
from ..main import MFPApp 

class FileIO(Processor):
	def __init__(self, init_type, init_args):
		self.filename = None 
		self.fileobj = None 

		Processor.__init__(self, 1, 1, init_type, init_args)
		initargs = self.parse_args(init_args)
		if len(initargs) > 0:
			self.filename = initargs[0]
			self.fileobj = open(self.filename, "r") 
	
	def trigger(self):
		cmd = self.inlets[0]
		if isinstance(cmd, MFPMethodCall):
			self.outputs[0] = cmd.call(self)
	
	def read(self, size=None):
		if size is None:
			return self.fileobj.read()
		else:
			return self.fileobj.read(size)

	def readline(self):
		return self.fileobj.readline()

def register():
	MFPApp.register("file", FileIO)

