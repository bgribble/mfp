#! /usr/bin/env python2.6
'''
rpc_wrapper.py:
Simple RPC manager working with Request/RequestPipe classes

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from request import Request
from . import log


def rpcwrap(worker_proc):
    def inner(self, *args, **kwargs):
        if self.local:
            return worker_proc(self, *args, **kwargs)
        else:
            rpcdata = dict(func=worker_proc.__name__, 
                           rpcid=self.rpcid, args=args, kwargs=kwargs)
            return self.call_remotely(rpcdata)
    return inner


class RPCMetaclass(type):
    def __init__(klass, name, bases, xdict):
        type.__init__(klass, name, bases, xdict)
        klass.register(name)


class RPCWrapper (object):
    __metaclass__ = RPCMetaclass

    NO_CLASS = -1
    NO_METHOD = -2
    METHOD_FAILED = -3
    METHOD_OK = -4

    class ClassNotFound(Exception):
        pass

    class MethodNotFound(Exception):
        pass

    class MethodFailed(Exception):
        def __init__(self, local, tb):
            self.traceback = tb
            if local:
                log.debug(tb)
            Exception.__init__(self)

    _rpcid_seq = 0
    rpcobj = {}
    rpctype = {}
    local = False
    pipe = None
    node_id = None
    call_stats = {} 

    def __init__(self, *args, **kwargs):
        self.rpcid = None
        
        if self.local:
            self.rpcid = RPCWrapper._rpcid_seq
            RPCWrapper._rpcid_seq += 1
            RPCWrapper.rpcobj[self.rpcid] = self
        else:
            r = Request(dict(func='__init__', type=type(self).__name__, 
                             args=args, kwargs=kwargs))
            type(self).pipe.put(r)
            type(self).pipe.wait(r)
            if r.response == RPCWrapper.NO_CLASS:
                raise RPCWrapper.ClassNotFound()

            self.rpcid = r.response

    def call_remotely(self, rpcdata):
        r = type(self).pipe.put(Request(rpcdata))
        type(self).pipe.wait(r)
        if r.response == RPCWrapper.METHOD_OK:
            return r.payload
        elif r.response == RPCWrapper.METHOD_FAILED:
            raise RPCWrapper.MethodFailed(False, r.payload)

    def call_locally(self, rpcdata):
        count = self.call_stats.get(rpcdata.get('func'), 0)
        self.call_stats[rpcdata.get('func')] = count + 1 

        methname = rpcdata.get('func')
        args = rpcdata.get('args')
        kwargs = rpcdata.get('kwargs')

        meth = getattr(self, methname)
        if meth:
            try:
                rv = meth(*args, **kwargs)
                return rv
            except Exception, e:
                import traceback
                raise RPCWrapper.MethodFailed(True, traceback.format_exc())
        else:
            raise RPCWrapper.MethodNotFound()

    @classmethod
    def register(klass, name):
        klass.rpctype[name] = klass

    @classmethod
    def handle(klass, req):
        rpcdata = req.payload
        func = rpcdata.get('func')
        rpcid = rpcdata.get('rpcid')
        args = rpcdata.get('args')
        kwargs = rpcdata.get('kwargs')

        req.state = Request.RESPONSE_DONE

        if func == '__init__':
            factory = RPCWrapper.rpctype.get(rpcdata.get('type'))
            if factory:
                obj = factory(*args, **kwargs)
                req.response = obj.rpcid
            else:
                req.response = RPCWrapper.NO_CLASS

        elif func == '__del__':
            del RPCWrapper.objects[rpcid]
            req.response = True

        else:
            obj = RPCWrapper.rpcobj.get(rpcid)
            try:
                req.payload = obj.call_locally(rpcdata)
                req.response = RPCWrapper.METHOD_OK
            except RPCWrapper.MethodNotFound, e:
                req.payload = None
                req.response = RPCWrapper.NO_METHOD
            except RPCWrapper.MethodFailed, e:
                req.payload = e.traceback
                req.response = RPCWrapper.METHOD_FAILED
            except Exception, e:
                import traceback
                einfo = "Method call failed for rpcid=%s node=%s\nobj=%s data=%s\n" % (rpcid,
                                                                                       RPCWrapper.node_id, obj, rpcdata)
                req.payload = einfo + traceback.format_exc()
                req.response = RPCWrapper.METHOD_FAILED
