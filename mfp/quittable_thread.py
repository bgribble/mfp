
from threading import Thread

class QuittableThread(Thread):
	_all_threads = [] 

	def __init__(self):
		self.join_req = False 
		QuittableThread._all_threads.append(self)
		Thread.__init__(self) 

	def finish(self):
		self.join_req = True 
		self.join() 
	
	@classmethod
	def finish_all(klass):
		for t in QuittableThread._all_threads:
			t.finish()

