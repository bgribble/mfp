#! /usr/bin/env python2.6
'''
singleton.py
Singleton metaclass

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
import threading


class Singleton(type):
    def __init__(klass, clsname, baseclasses, clsdict):
        klass._singleton_lock = threading.Lock()
        klass._singleton = None

    def __call__(klass, *args, **kwargs):
        with klass._singleton_lock:
            if klass._singleton is None:
                klass._singleton = super(Singleton, klass).__call__(*args, **kwargs)
            return klass._singleton
