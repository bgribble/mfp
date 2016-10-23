#! /usr/bin/env python2.6
'''
rpc_wrapper.py:
Simple RPC-able class wrapper working with RPCHost

Copyright (c) 2010-2014 Bill Gribble <grib@billgribble.com>
'''

from request import Request
from mfp import log

def rpcwrap(worker_proc):
    def inner(self, *args, **kwargs):
        if self.local:
            return worker_proc(self, *args, **kwargs)
        else:
            rpcdata = dict(func=worker_proc.__name__, 
                           rpcid=self.rpcid, args=args, kwargs=kwargs)
            return self.call_remotely(rpcdata)
    return inner

def rpcwrap_noresp(worker_proc):
    def inner(self, *args, **kwargs):
        if self.local:
            return worker_proc(self, *args, **kwargs)
        else:
            rpcdata = dict(func=worker_proc.__name__, 
                           rpcid=self.rpcid, args=args, kwargs=kwargs)
            return self.call_remotely(rpcdata, response=False)
    return inner

class RPCMetaclass(type):
    def __init__(klass, name, bases, xdict):
        type.__init__(klass, name, bases, xdict)
        klass.register(name)
        klass.publishers = []


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
    rpchost = None
    call_stats = {} 

    def __init__(self, *args, **kwargs):
        self.rpcid = None
        self.peer_id = None 
       
        if self.local:
            self.rpcid = RPCWrapper._rpcid_seq
            RPCWrapper._rpcid_seq += 1
            RPCWrapper.rpcobj[self.rpcid] = self
        else:
            r = Request("create", dict(type=type(self).__name__, 
                                       args=args, kwargs=kwargs))
            self.peer_id = kwargs.get("peer_id")
            if self.peer_id is None:
                if self.publishers: 
                    self.peer_id = self.publishers[0]
                else:
                    self.peer_id = 0

            self.rpchost.put(r, self.peer_id)
            self.rpchost.wait(r)
            if not r.result or r.result[0] == RPCWrapper.NO_CLASS:
                raise RPCWrapper.ClassNotFound()

            self.rpcid = r.result[1]

    def call_remotely(self, rpcdata, response=True):
        from datetime import datetime 

        r = Request("call", rpcdata)
        call_started = datetime.now()
        r.diagnostic["remote_call_start"] = str(call_started)
        if not response: 
            r.request_id = None

        try: 
            self.rpchost.put(r, self.peer_id)
        except Exception as e: 
            log.debug("[call_remotely] Error in RPC operation:", e)
            return None 

        puttime = str(datetime.now())
        if response: 
            self.rpchost.wait(r, timeout=10)
        call_complete = datetime.now()
        call_elapsed = call_complete - call_started
        r.diagnostic["remote_call_complete"] = call_complete 
        r.diagnostic["remote_call_put"] = puttime 

        callinfo = self.call_stats.setdefault(rpcdata.get('func'), {})
        total = callinfo.get("total")
        if total:
            total += call_elapsed 
        else: 
            total = call_elapsed 
        callinfo["total"] = total 
        count = callinfo.get("count", 0) + 1
        callinfo["count"] = count 
        callinfo["avgtime"] = total / count 


        if not response:
            return None 
        elif not r.result: 
            print "FIXME: no result should return a deferment"
            return None 

        status, retval = r.result 
        if status == RPCWrapper.METHOD_OK:
            return retval 
        elif status == RPCWrapper.METHOD_FAILED:
            raise RPCWrapper.MethodFailed(False, retval)

    def call_locally(self, rpcdata):
        callinfo = self.call_stats.setdefault(rpcdata.get('func'), {})
        count = callinfo.get("local", 0) + 1 
        callinfo["local"] = count

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

