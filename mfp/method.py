

class MethodCall(object): 
	def __init__(self, method, args, kwargs):
		self.method = method
		self.args = args
		self.kwargs = kwargs

	def call(self, target):
		m = target.__dict__.get(self.method)
		if callable(m):
			return m(target, *self.args, **self.kwargs)

