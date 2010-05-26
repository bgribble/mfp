#! /usr/bin/env python2.6
'''
request.py 
Request/response management for multiprocessing queue pairs 
'''

class QRequest (object):
	_next_id = 1
	def __init__(self, payload):
		self.req_id = QRequest._next_id
		self.payload = payload 
		QRequest._next_id += 1

class QResponse (object):
	def __init(self, req, payload):
		self.req_id = req.req_id
		self.payload = payload 
		
