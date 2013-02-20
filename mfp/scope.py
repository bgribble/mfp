#! /usr/bin/env python
'''
scope.py
Lexical scope helper

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''


class LexicalScope (object):
    def __init__(self):
        self.bindings = {}

    def _mkunique(self, name):
        basename = name 
        testname = name 
        counter = 1
        fmt = "%03d"

        while self.bindings.has_key(testname):
            counter += 1
            if counter > 999:
                fmt = "%d"
            
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
        return self.bindings.get(name)
