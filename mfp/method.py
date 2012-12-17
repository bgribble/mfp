#! /usr/bin/env python2.6
'''
method.py: MethodCall wrapper for passing messages to objects

Copyright (c) 2011-2012 Bill Gribble <grib@billgribble.com>
'''
from mfp import log


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

    def call(self, target):
        try:
            m = getattr(target, self.method)
        except AttributeError, e:
            raise Exception("Method %s not found for %s" % (self.method, target))

        if callable(m):
            try:
                return m(*self.args, **self.kwargs)
            except Exception, e:
                raise Exception("Method %s for %s raised exception %s"
                                % (self.method, target, e))
        elif self.fallback:
            try:
                return self.fallback([self] + self.args, **self.kwargs)
            except Exception, e:
                raise Exception("Method %s for %s raised exception %s"
                                % (self.method, target, e))
        else:
            log.debug("MethodCall.call():", target, self.method, m, type(m))
            raise Exception("Method %s cannot be called" % self.method)
