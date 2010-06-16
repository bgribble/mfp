#! /usr/bin/env python2.6
'''
request.py 
Request object for use with RequestPipe
'''

class Request(object):
	_next_id = 0 

	CREATED = 0 
	SUBMITTED = 1
	RESPONSE_PEND = 2
	RESPONSE_RCVD = 3 
	
	def __init__(self, payload, callback=None, multi_cb=False):
		self.state = Request.CREATED 
		self.payload = payload
		self.response = None 
		self.callback = callback
		self.multi_cb = multi_cb
		self.request_id = Request._next_id
		Request._next_id += 1
	

