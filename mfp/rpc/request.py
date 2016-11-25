#! /usr/bin/env python2.6
'''
request.py
Request object for use with RequestPipe
'''

import simplejson as json


def _dumb_load(ctor, values):
    initobj = ctor()
    for attr, value in values.items():
        setattr(initobj, attr, value)
    return initobj

def ext_encode (klass):
    ExtendedEncoder.TYPES['__' + klass.__name__ + '__'] = klass
    return klass

class ExtendedEncoder (json.JSONEncoder):
    from ..bang import BangType, UninitType
    from ..gui.colordb import RGBAColor 
    from ..gui.ticks import ScaleType 

    TYPES = { '__BangType__': BangType, 
             '__UninitType__': UninitType, 
             '__RGBAColor__': RGBAColor}

    DUMBTYPES = (ScaleType,)

    def default(self, obj):
        if isinstance(obj, tuple(ExtendedEncoder.TYPES.values())):
            key = "__%s__" % obj.__class__.__name__
            return {key: obj.__dict__ }
        elif isinstance(obj, self.DUMBTYPES):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def extended_decoder_hook (saved):
    from ..bang import Bang, Uninit
    if (isinstance(saved, dict) and len(saved.keys()) == 1):
        tname, tdict = saved.items()[0]
        if tname == "__BangType__":
            return Bang
        elif tname == "__UninitType__":
            return Uninit
        else: 
            ctor = ExtendedEncoder.TYPES.get(tname)
            if ctor:
                if hasattr(ctor, 'load'):
                    return ctor.load(tdict)
                else:
                    return _dumb_load(ctor, tdict)
    return saved 


class Request(object):
    _next_id = 0

    CREATED = 0
    SUBMITTED = 1
    RESPONSE_PEND = 2
    RESPONSE_DONE = 3
    RESPONSE_RCVD = 4
    RPC_ERROR = 5

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
        #obj["diagnostic"] = self.diagnostic

        return json.dumps(obj, cls=ExtendedEncoder)

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

