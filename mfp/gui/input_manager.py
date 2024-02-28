#! /usr/bin/env python
'''
input_manager.py: Handle keyboard and mouse input and route through input modes

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import inspect

from .backend_interfaces import BackendInterface
from .input_mode import InputMode
from .key_sequencer import KeySequencer
from ..gui_main import MFPGUI


class InputManagerImpl(ABC):
    @abstractmethod
    def handle_event(self, *args):
        pass


class InputManager(BackendInterface):
    class InputNeedsRequeue (Exception):
        pass

    def __init__(self, window):
        self.window = window
        self.global_mode = None
        self.major_mode = None
        self.minor_modes = []
        self.minor_seqno = 0
        self.keyseq = KeySequencer()
        self.root_source = None
        self.pointer_x = None
        self.pointer_y = None
        self.pointer_ev_x = None
        self.pointer_ev_y = None
        self.pointer_obj = None
        self.pointer_obj_time = None
        self.pointer_leave_time = None
        self.pointer_lastobj = None
        self.hover_thresh = timedelta(microseconds=750000)

        MFPGUI().async_task(self.hover_monitor())

    @classmethod
    def build(cls, *args, **kwargs):
        return cls.get_backend(MFPGUI().backend_name)(*args, **kwargs)

    async def hover_monitor(self):
        while True:
            if self.pointer_obj_time is not None:
                elapsed = datetime.now() - self.pointer_obj_time
                if elapsed > self.hover_thresh:
                    await self._hover_handler()
            await asyncio.sleep(0.2)

    async def _hover_handler(self):
        handlers = self.get_handlers(self.keyseq.canonicalize("HOVER"))
        for handler in handlers:
            rv = handler()
            if inspect.isawaitable(rv):
                rv = await rv
            if rv:
                return True
        return False

    def global_binding(self, key, action, helptext=''):
        self.global_mode.bind(key, action, helptext)

    def set_major_mode(self, mode):
        if isinstance(self.major_mode, InputMode):
            self.major_mode.disable()
        self.major_mode = mode
        mode.enable()
        self.window.display_bindings()

    def enable_minor_mode(self, mode):
        def modekey(a):
            return -a.affinity, -a.seqno

        do_enable = True
        if mode in self.minor_modes:
            self.minor_modes.remove(mode)
            do_enable = False

        mode.seqno = self.minor_seqno
        self.minor_seqno += 1
        self.minor_modes[:0] = [mode]
        self.minor_modes.sort(key=modekey)
        self.window.display_bindings()

        if do_enable:
            mode.enable()

    def disable_minor_mode(self, mode):
        if mode not in self.minor_modes:
            return

        cb = mode.disable()
        if inspect.isawaitable(cb):
            MFPGUI().async_task(cb)
        self.minor_modes.remove(mode)
        self.window.display_bindings()

    def synthesize(self, key):
        self.keyseq.sequences.append(key)

    def get_handlers(self, keysym):
        handlers = []
        if keysym is not None:
            # check minor modes first
            for minor in self.minor_modes:
                handler = minor.lookup(keysym)
                if handler is not None:
                    handlers.append(handler[0])

            # then major mode
            if self.major_mode is not None:
                handler = self.major_mode.lookup(keysym)
                if handler is not None:
                    handlers.append(handler[0])

            # then global
            handler = self.global_mode.lookup(keysym)
            if handler is not None:
                handlers.append(handler[0])

        return handlers
