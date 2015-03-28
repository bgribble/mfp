#! /usr/bin/env python2.6
'''
input_mode.py: InputMode parent class for managing key/mouse bindings and interaction

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from mfp import log


class InputMode (object):
    def __init__(self, description='', short_description=None):
        self.description = description
        if short_description is not None:
            self.short_description = short_description
        else:
            self.short_description = self.description 
        
        self.enabled = False 
        self.default = None
        self.bindings = {}
        self.extensions = []
        self.num_bindings = 0
        self.affinity = 0
        self.seqno = None

    def extend(self, mode):
        self.extensions.append(mode)

    def bind(self, keysym, action, helptext=None):
        if keysym is None:
            self.default = (action, helptext, self.num_bindings)
        else:
            self.bindings[keysym] = (action, helptext, self.num_bindings)
        self.num_bindings += 1

    def directory(self):
        listing = []
        items = self.bindings.items()
        items.sort(key=lambda e: e[1][2])
        for keysym, value in items:
            if value[1] is not None:
                listing.append((keysym, value[1]))
        if self.default is not None:
            listing.append(("[default]", self.default[1]))
        for e in self.extensions:
            listing.extend(e.directory())
        return listing

    def lookup(self, keysym):
        # first check our direct bindings
        binding = self.bindings.get(keysym)
        if binding is not None:
            return binding

        # if any extensions are specified, look in them
        # (but don't use extension defaults)
        for ext in self.extensions:
            binding = ext.bindings.get(keysym)
            if binding is not None:
                return binding

        # do we have a default? They get an extra arg (the keysym)
        if self.default is not None:
            newfunc = lambda: self.default[0](keysym)
            return (newfunc, self.default[1], self.default[2])

        # do extensions have a default:
        for ext in self.extensions:
            if ext.default is not None:
                newfunc = lambda: ext.default[0](keysym)
                return (newfunc, ext.default[1], ext.default[2])

        return None

    def enable(self):
        self.enabled = True 
        for ext in self.extensions: 
            ext.enable()

    def disable(self):
        self.enabled = False 
        for ext in self.extensions: 
            ext.disable()

    def __repr__(self):
        return "<InputMode %s>" % self.description
