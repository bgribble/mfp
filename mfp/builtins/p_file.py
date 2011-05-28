
from ..processor import Processor
from ..main import MFPApp 
from ..method import MethodCall

class FileIO(Processor):
	def __init__(self, init_type, init_args):
		self.filename = None 
		self.fileobj = None 
		self.mode = "r"

		Processor.__init__(self, 1, 1, init_type, init_args)
		initargs = self.parse_args(init_args)
		if len(initargs) > 0:
			self.filename = initargs[0]
		if len(initargs) > 1:
			self.mode = initargs[1]
		if self.filename:
			self.open()
	
	def trigger(self):
		cmd = self.inlets[0]
		if isinstance(cmd, MethodCall):
			self.outlets[0] = cmd.call(self)
		else:
			self.fileobj.write(cmd)
	
	def read(self, size=None):
		if size is None:
			return self.fileobj.read()
		else:
			return self.fileobj.read(size)

	def readline(self):
		return self.fileobj.readline()

	def readlines(self):
		return self.fileobj.readlines()

	def open(self, filename=None, mode=None):
		if filename is not None:
			self.filename = filename
		if mode is not None:
			self.mode = mode
		if self.filename is not None:
			if self.fileobj:
				self.close()
			self.fileobj = open(self.filename, self.mode)

	def close(self):
		if self.fileobj:
			self.fileobj.close()
			self.fileobj = None

def register():
	MFPApp().register("file", FileIO)

