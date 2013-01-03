#! /usr/bin/env python2.6
'''
singleton.py
Singleton metaclass

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import threading

class SingletonMeta (type):
    def __init__(self, clsname, baseclasses, clsdict):
        self._singleton_lock = threading.RLock()
        self._singleton = None

    def __new__(self, name, bases, dict):
        #print "SingletonMeta.__new__(", self, name, bases, dict, ")"
        return type.__new__(self, name, bases, dict)

    def __call__(self, *args, **kwargs):
        #print "SingletonMeta.__call__(", self, args, kwargs, ")"
        with self._singleton_lock:
            if self._singleton is None:
                self._singleton = super(SingletonMeta, self).__call__(*args, **kwargs)
            return self._singleton

class Singleton (object):
    __metaclass__ = SingletonMeta

    @classmethod
    def __new__(cls, *args):
        #print "Singleton.__new__(", args, ")"
        with cls._singleton_lock:
            if cls._singleton is None:
                #print "No singleton, returning new object"
                return object.__new__(cls)
            else:
                #print "Singleton exists, returning it"
                return cls._singleton

    def __getnewargs__(self):
        # defining __getnewargs__ ensures that __new__ is called when 
        # unpickling a Singleton
        return ()

