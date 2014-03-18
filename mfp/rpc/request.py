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
        self.result = None
        self.callback = callback
        self.request_id = Request._next_id
        self.diagnostic = {}
        Request._next_id += 1

    def serialize(self):
        obj = dict(jsonrpc="2.0", id=self.request_id)
        
        if self.method is not None:
            obj["method"] = self.method
            obj["params"] = self.params
        else: 
            obj["result"] = self.result
        obj["diagnostic"] = self.diagnostic

        return json.dumps(obj)

    def is_request(self):
        return (self.method is not None)

    def is_response(self):
        return (self.result is not None)

    @classmethod
    def from_dict(cls, obj):
        req = Request(obj.get("method"), obj.get("params"))

        if obj.has_key("id"):
            req.request_id = obj['id']

        if obj.has_key("diagnostic"):
            req.diagnostic = obj['diagnostic']

        if obj.has_key("error"):
            # a response 
            req.result = obj['error']
        elif obj.has_key("result"):
            req.result = obj['result']
            if req.result is not None:
                req.state = Request.RESPONSE_RCVD
            # a notification
        return req

    def __repr__(self):
        return "<Request %s %s %s %s>" % (self.request_id, self.method, self.params,
                                          self.result)

