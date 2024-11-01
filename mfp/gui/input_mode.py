#! /usr/bin/env python
'''
input_mode.py: InputMode parent class for managing key/mouse bindings and interaction

Copyright (c) Bill Gribble <grib@billgribble.com>
'''
import inspect
from mfp import log


class InputMode:
    _registry = {}

    # will be separate for each subclass
    _bindings = {}
    _default = None
    _num_bindings = 0

    def __init__(self, description='', short_description=None):
        self.description = description
        if short_description is not None:
            self.short_description = short_description
        else:
            self.short_description = self.description

        self.enabled = False
        self.affinity = 0
        self.seqno = None

        # FIXME
        self.default = None
        self.bindings = {}
        self.extensions = []

    @classmethod
    def __init_subclass__(cls, **kwargs):
        InputMode._registry[cls.__name__] = cls
        super().__init_subclass__(**kwargs)
        cls._bindings = {}
        cls._default = None
        cls._num_bindings = 0

        if hasattr(cls, "init_bindings"):
            cls.init_bindings()

    async def setup(self):
        for mode in self.extensions:
            await mode.setup()

    def extend(self, mode):
        self.extensions.append(mode)

    @classmethod
    def cl_bind(cls, label, action, helptext=None, keysym=None, menupath=None):
        if keysym is None:
            cls._default = (action, helptext, cls._num_bindings)
        else:
            cls._bindings[keysym] = (label, action, helptext, cls._num_bindings, keysym, menupath)
        cls._num_bindings += 1

    def bind(self, keysym, action, helptext=None):
        if keysym is None:
            self.default = (action, helptext, type(self)._num_bindings, keysym, None)
        else:
            self.bindings[keysym] = (action, helptext, type(self)._num_bindings, keysym, None)
        type(self)._num_bindings += 1

    def directory(self):
        listing = []
        items = list(self.bindings.items())
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

        # class bindings (tuple is different)
        binding = type(self)._bindings.get(keysym)
        if binding is not None:
            return (
                lambda: binding[1](self), *binding[2:]
            )

        # if any extensions are specified, look in them
        # (but don't use extension defaults)
        for ext in self.extensions:
            binding = ext.bindings.get(keysym)
            if binding is not None:
                return binding

        # do we have a default? They get an extra arg (the keysym)
        if self.default is not None:
            newfunc = lambda: self.default[0](keysym)
            return (newfunc, *self.default[1:])

        # class default
        if type(self)._default is not None:
            newfunc = lambda: type(self)._default[1](self, keysym)
            return (newfunc, *self.default[2:])

        # do extensions have a default:
        for ext in self.extensions:
            if ext.default is not None:
                newfunc = lambda: ext.default[0](keysym)
                return (newfunc, *ext.default[1:])

        return None

    def enable(self):
        self.enabled = True
        for ext in self.extensions:
            cb = ext.enable()
            if inspect.isawaitable(cb):
                MFPGUI().async_task(cb)

    def disable(self):
        self.enabled = False
        for ext in self.extensions:
            cb = ext.disable()
            if inspect.isawaitable(cb):
                MFPGUI().async_task(cb)

    def __repr__(self):
        return "<InputMode %s>" % self.description
