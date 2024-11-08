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
    helptext: str
    index: int
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
    _num_bindings = 0

    # will be separate for each subclass
    _bindings = {}
    _extensions = []

    _default = None
    _mode_prefix = ''

    def __init__(self, description='', short_description=None):
        self.description = description
        if short_description is not None:
            self.short_description = short_description
        else:
            self.short_description = self.description

        self.extensions = []
        self.enabled = False
        self.affinity = 0
        self.seqno = None

    @classmethod
    def __init_subclass__(cls, **kwargs):
        InputMode._registry[cls.__name__] = cls
        super().__init_subclass__(**kwargs)
        cls._bindings = {}
        cls._default = None

        if hasattr(cls, "init_bindings"):
            cls.init_bindings()

    async def setup(self):
        for mode in self.extensions:
            await mode.setup()

    def extend(self, mode):
        """
        extend associates mode objects
        """
        self.extensions.append(mode)

    @classmethod
    def extend_mode(cls, mode_type):
        """
        extend_mode associates the mode TYPES so we can find bindings
        """
        cls._extensions.append(mode_type)

    @classmethod
    def bind(cls, label, action, helptext=None, keysym=None, menupath=None):
        """
        binding at the class level lets us know what the mode's
        bindings are before we create an instance of it
        """
        if keysym is None:
            log.debug(f"[bind] defaulting for {cls} to {label} {action} {helptext} {keysym} {menupath}")
            cls._default = Binding(
                "default", action, helptext, InputMode._num_bindings, None, None, cls
            )
        else:
            binding = Binding(
                label, action, helptext, InputMode._num_bindings, keysym, menupath, cls
            )
            cls._bindings[keysym] = binding
            InputMode._bindings_by_label[label] = binding

        InputMode._num_bindings += 1

    def directory(self):
        listing = []
        items = list(self._bindings.items())
        items.sort(key=lambda e: e[1].index)
        for keysym, binding in items:
            if binding.keysym is not None:
                listing.append((keysym, binding.helptext))
        if self._default is not None:
            listing.append(("[default]", self._default.helptext))
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
                action=lambda *args, **kwargs: binding.action(self, *args, **kwargs)
            )

    def lookup(self, keysym):
        # class bindings (action is not bound to instance yet)
        binding = type(self)._bindings.get(keysym)
        if binding is not None:
            return binding.copy(
                action=lambda *args, **kwargs: binding.action(self, *args, **kwargs)
            )

        # if any extensions are specified, look in them
        # (but don't use extension defaults)
        for ext in self.extensions:
            binding = ext.lookup(keysym)
            if binding is not None:
                return binding

        # class default
        if type(self)._default is not None:
            binding = type(self)._default
            return binding.copy(
                action=lambda *args, **kwargs: binding.action(self, keysym, *args, **kwargs)
            )

        # do extensions have a default:
        for ext in self.extensions:
            if ext._default is not None:
                binding = ext._default
                return binding.copy(
                    action=lambda *args, **kwargs: binding.action(self, keysym, *args, **kwargs)
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
