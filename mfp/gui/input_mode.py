#! /usr/bin/env python
'''
input_mode.py: InputMode parent class for managing key/mouse bindings and interaction

Copyright (c) Bill Gribble <grib@billgribble.com>
'''
import inspect
import dataclasses
from dataclasses import dataclass
from mfp import log

@dataclass
class Binding:
    label: str
    action: callable
    index: int
    helptext: str
    keysym: str
    menupath: str = ''
    mode: any = None
    enabled: bool = False

    def copy(self, **kwargs):
        return Binding(**{
            **{field.name: getattr(self, field.name) for field in dataclasses.fields(self)},
            **kwargs
        })


class InputMode:
    _registry = {}

    # global for all modes
    _bindings_by_label = {}

    # will be separate for each subclass
    _bindings = {}
    _default = None
    _num_bindings = 0
    _mode_prefix = ''

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
        """
        after migrating all modes to cl_bind, will rename this to bind

        binding at the class level lets us know what the mode's
        bindings are before we create an instance of it
        """
        if keysym is None:
            cls._default = Binding(
                "default", action, helptext, cls._num_bindings, None, None, cls
            )
        else:
            binding = Binding(
                label, action, helptext, cls._num_bindings, keysym, menupath, cls
            )
            cls._bindings[keysym] = binding
            InputMode._bindings_by_label[label] = binding

        cls._num_bindings += 1

    def bind(self, keysym, action, helptext=None):
        if keysym is None:
            self.default = Binding(None, action, helptext, type(self)._num_bindings, keysym, None)
        else:
            self.bindings[keysym] = Binding(None, action, helptext, type(self)._num_bindings, keysym, None)
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

    def lookup_by_label(self, label):
        """
        look up class bindings by label. Used for commandline eval.
        """
        binding = type(self)._bindings.get(label)
        if binding is not None:
            return binding.copy(
                action=lambda: binding.action(self)
            )

    def lookup(self, keysym):
        # first check our direct bindings
        binding = self.bindings.get(keysym)
        if binding is not None:
            return binding

        # class bindings (action is not bound to instance yet)
        binding = type(self)._bindings.get(keysym)
        if binding is not None:
            return binding.copy(
                action=lambda: binding.action(self)
            )

        # if any extensions are specified, look in them
        # (but don't use extension defaults)
        for ext in self.extensions:
            binding = ext.bindings.get(keysym)
            if binding is not None:
                return binding

        # do we have a default? They get an extra arg (the keysym)
        if self.default is not None:
            return self.default.copy(
                action=lambda: self.default.action(keysym)
            )

        # class default
        if type(self)._default is not None:
            binding = type(self)._default
            return binding.copy(
                action=lambda: binding.action(self, keysym)
            )

        # do extensions have a default:
        for ext in self.extensions:
            if ext.default is not None:
                binding = ext.default
                return binding.copy(
                    action=lambda: binding.action(keysym)
                )

        return None

    def enable(self):
        from mfp.gui_main import MFPGUI
        self.enabled = True
        for ext in self.extensions:
            cb = ext.enable()
            if inspect.isawaitable(cb):
                MFPGUI().async_task(cb)

    def disable(self):
        from mfp.gui_main import MFPGUI
        self.enabled = False
        for ext in self.extensions:
            cb = ext.disable()
            if inspect.isawaitable(cb):
                MFPGUI().async_task(cb)

    def __repr__(self):
        return "<InputMode %s>" % self.description
