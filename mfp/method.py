#! /usr/bin/env python
'''
method.py: MethodCall wrapper for passing messages to objects

Copyright (c) 2011-2012 Bill Gribble <grib@billgribble.com>
'''
from mfp import log


class MethodCallError (Exception):
    pass


class MethodCall(object):
    def __init__(self, method, *args, **kwargs):
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self.fallback = None

        try:
            # this is a backdoor method, where we just want to call any
            # python function of one argument on this object
            from .evaluator import Evaluator
            ev = Evaluator()
            meth = ev.eval(self.method)
            if callable(meth):
                self.fallback = meth
        except:
            # it's OK if this fails, that just means there's no global
            # with that name and we will have to look up the method on
            # whatever object it hits at runtime
            pass

    def __str__(self):
        args = ', '.join([repr(a) for a in self.args]) if self.args else ''
        kwargs = ', '.join([
            f"{key}={repr(value)}" for key, value in self.kwargs.items()
        ]) if self.kwargs else ''

        siglist = [item for item in [args, kwargs] if item]

        return f"@{self.method}({', '.join(siglist)})"

    @classmethod
    def load(cls, objdict):
        m =  MethodCall(
            objdict.get("method"),
            *objdict.get("args", []),
            **objdict.get("kwargs", {})
        )
        return m

    def call(self, target):
        try:

            m = getattr(target, self.method)
        except AttributeError:
            raise MethodCallError("Method '%s' not found for type '%s'" % (self.method, target.init_type))

        if callable(m):
            try:
                return m(*self.args, **self.kwargs)
            except Exception as e:
                log.debug("Error calling", self.method, "on", target)
                log.debug("args=%s, kwargs=%s" % (self.args, self.kwargs))
                log.debug_traceback(e)
                raise MethodCallError("Method '%s' for type '%s' raised exception '%s' %s"
                                      % (self.method, target.init_type, e, type(e)))
        elif self.fallback:
            try:
                return self.fallback([self] + self.args, **self.kwargs)
            except Exception as e:
                raise MethodCallError(
                    "Method fallback '%s' for type '%s' raised exception '%s'"
                    % (self.method, target.init_type, e)
                )
        else:
            log.debug("MethodCall.call():", target, self.method, m, type(m))
            raise MethodCallError(
                "Method '%s' of type '%s' cannot be called"
                % (self.method, target.init_type)
            )
