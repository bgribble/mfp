#! /usr/bin/env python
'''
scope.py
Lexical scope helper

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import re 
from .bang import Unbound 

class LexicalScope (object):
    def __init__(self, name, clonenum=0):
        self.name = name 
        self.bindings = {}
        self.clonenum = clonenum 

    def _mkunique(self, name):
        basename = name 
        testname = name 
        counter = 1
        fmt = "_%03d"
        
        m = re.search("_[0-9]{3}$", name) 
        if m:
            basename = name[:-4]

        while testname in self.bindings:
            counter += 1
            if counter > 999:
                fmt = "_%d"
            
            testname = basename + fmt % counter
        return testname 

    def bind(self, name, obj):
        name_bound = self._mkunique(name)
        self.bindings[name_bound] = obj
        return name_bound

    def unbind(self, name):
        try:
            del self.bindings[name]
            return True
        except KeyError:
            return False

    def query(self, name):
        try:
            return (True, self.bindings[name])
        except KeyError:
            return (False, None)

    def resolve(self, name):
        return self.bindings.get(name, Unbound)

class NaiveScope (LexicalScope): 
    def __init__(self): 
        LexicalScope.__init__(self, "")

    def bind(self, name, obj):
        self.bindings[name] = obj 
        return name 


