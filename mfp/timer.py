#! /usr/bin/env python2.6
'''
timer.py
Multi-timer implementation
'''
from threading import Thread, Condition, Lock 
from datetime import datetime, timedelta

def tdmag(td):
	return (td.days * 86400000 + td.seconds * 1000 + td.microseconds / 1000.0) / 1000.0

class MultiTimer(Thread):
	def __init__(self):
		Thread.__init__(self)

		self.scheduled = [] 
		self.lock = Lock()
		self.cv = Condition(self.lock)
		self.tolerance = timedelta(microseconds=1000)
		self.join_req = False 
		
	def schedule(self, deadline, callback, data=[]):
		with self.lock:
			if not self.scheduled:
				self.scheduled.append((deadline, callback, data))
			else:
				self.scheduled.append((deadline, callback, data))
				self.scheduled.sort(key=lambda x: x[0])
			self.cv.notify()
	
	def run(self):
		while not self.join_req:
			looptime = datetime.now()
			timedout = [] 
			with self.lock:
				if not self.scheduled:
					self.cv.wait(.1)
				else:
					while (self.scheduled 
						   and (looptime > (self.scheduled[0][0] - self.tolerance))):
						timedout.append(self.scheduled[0])
						self.scheduled[:1] = [] 

			for deadline, callback, data in timedout: 
				callback(*data)

			looptime = datetime.now()
			with self.lock:
				if self.scheduled:
					sleeptime = self.scheduled[0][0] - looptime
					if sleeptime > self.tolerance: 
						self.cv.wait(tdmag(sleeptime))

def ptime(sched):
	t = datetime.now()
	print "Scheduled: %s, actual: %s, diff: %s" % (sched, t, t-sched)


if __name__ == "__main__":
	t = MultiTimer()
	t.start()

	print "Scheduling pings."
	starttime = datetime.now()
	t.schedule(starttime + timedelta(milliseconds=1100), ptime, 
			   [starttime + timedelta(milliseconds=1100)])

	t.schedule(starttime + timedelta(milliseconds=1000), ptime, 
			   [starttime + timedelta(milliseconds=1000)])

	t.schedule(starttime + timedelta(milliseconds=1000), ptime, 
			   [starttime + timedelta(milliseconds=1000)])

	t.schedule(starttime + timedelta(milliseconds=1000), ptime, 
			   [starttime + timedelta(milliseconds=1000)])

	t.schedule(starttime + timedelta(milliseconds=1200), ptime, 
			   [starttime + timedelta(milliseconds=1200)])




