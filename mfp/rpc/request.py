#! /usr/bin/env python2.6
'''
request.py
Request object for use with RequestPipe
'''

import simplejson as json

class Request(object):
    _next_id = 0

    CREATED = 0
    SUBMITTED = 1
    RESPONSE_PEND = 2
    RESPONSE_DONE = 3
    RESPONSE_RCVD = 4

    def __init__(self, method, params, callback=None):
        self.state = Request.CREATED
        self.method = method
        self.params = params 
        self.response = None
        self.callback = callback
        self.request_id = Request._next_id
        Request._next_id += 1

    def serialize(self):
        obj = dict(jsonrpc="2.0", id=self.request_id, method=self.method, 
                   result=self.response, params=self.params)
        return json.dumps(obj)

    def is_request(self):
        return (self.method is not None)

    def is_response(self):
        return (self.response is not None)

    @classmethod
    def from_dict(cls, obj):
        req = Request(obj.get("method"), obj.get("params"))

        if obj.has_key("id"):
            req.request_id = obj['id']

        if obj.has_key("error"):
            # a response 
            req.response = obj['error']
        elif obj.has_key("result"):
            req.response = obj['result']
            if req.response is not None:
                req.state = Request.RESPONSE_RCVD
            # a notification
        return req

    def __repr__(self):
        return "<Request %s %s %s %s>" % (self.request_id, self.method, self.params,
                                          self.response)

