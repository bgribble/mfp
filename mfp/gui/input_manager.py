#! /usr/bin/env python
'''
input_manager.py: Handle keyboard and mouse input and route through input modes

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

import asyncio
from datetime import datetime, timedelta
import inspect

from mfp import log

from .input_mode import InputMode
from .key_sequencer import KeySequencer
from .event import (
    KeyPressEvent,
    KeyReleaseEvent,
    ButtonPressEvent,
    ButtonReleaseEvent,
    ScrollEvent,
    MotionEvent,
    EnterEvent,
    LeaveEvent,
)
from ..gui_main import MFPGUI


class InputManager:
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

    async def run_handlers(self, handlers, keysym, coro=None, offset=-1):
        retry_count = 0
        current_handler = None
        while retry_count < 5:
            try:
                for index, handler in enumerate(handlers):
                    # this is for the case where we were iterating over
                    # handlers and found one async, and are restarting in
                    # the middle of the loop, but async
                    current_handler = handler
                    if index < offset:
                        continue
                    elif retry_count == 0 and index == offset:
                        rv = coro
                    else:
                        rv = handler()

                    if inspect.isawaitable(rv):
                        rv = await rv
                    if rv:
                        return True
                return False
            except InputManager.InputNeedsRequeue:
                # handlers might have changed in the previous handler
                handlers = self.get_handlers(keysym)
                retry_count += 1
                offset = -1
            except Exception as e:
                log.error(
                    f"[run_handlers] Exception while handling key command {keysym}: {e} {current_handler}"
                )
                log.debug_traceback(e)
                return False

    def handle_keysym(self, keysym):
        if not keysym:
            return True

        handlers = self.get_handlers(keysym)
        current_handler = None
        retry_count = 0

        if not handlers:
            return False

        while retry_count < 5:
            try:
                for item, handler in enumerate(handlers):
                    current_handler = handler
                    handler_rv = handler()
                    if inspect.isawaitable(handler_rv):
                        MFPGUI().async_task(self.run_handlers(
                            handlers, keysym, coro=handler_rv, offset=item
                        ))
                        return True
                    if handler_rv:
                        return True
                return False
            except InputManager.InputNeedsRequeue:
                handlers = self.get_handlers(keysym)
                retry_count += 1
            except Exception as e:
                log.error(
                    f"[handle_keysym] Exception while handling key command {keysym}: {e} {current_handler}"
                )
                log.debug_traceback(e)
                return False
        return False

    def handle_event(self, *args):
        _, event = args

        keysym = None
        if isinstance(event, (
            KeyPressEvent, KeyReleaseEvent, ButtonPressEvent, ButtonReleaseEvent,
            ScrollEvent
        )):
            try:
                self.keyseq.process(event)
            except Exception as e:
                log.error(f"[handle_event] Exception handling {event}: {e}")
                raise
            if len(self.keyseq.sequences) > 0:
                keysym = self.keyseq.pop()

        elif isinstance(event, MotionEvent):
            # FIXME: if the scaling changes so that window.stage_pos would return a
            # different value, that should generate a MOTION event.  Currently we are
            # just kludging pointer_x and pointer_y from the scale callback.
            self.pointer_ev_x = event.x
            self.pointer_ev_y = event.y
            self.pointer_x, self.pointer_y = (
                self.window.screen_to_canvas(event.x, event.y)
            )
            self.keyseq.process(event)
            if len(self.keyseq.sequences) > 0:
                keysym = self.keyseq.pop()

        elif isinstance(event, EnterEvent):
            src = event.target
            now = datetime.now()
            if (
                self.pointer_leave_time is not None
                and (now - self.pointer_leave_time) > timedelta(milliseconds=100)
            ):
                self.keyseq.mod_keys = set()
                self.window.grab_focus()

            if (
                src
                and src != self.window
                and self.window.object_visible(src)
            ):
                self.pointer_obj = src
                self.pointer_obj_time = now

        elif isinstance(event, LeaveEvent):
            src = event.target
            self.pointer_leave_time = datetime.now()
            if src == self.pointer_obj:
                self.pointer_lastobj = self.pointer_obj
                self.pointer_obj = None
                self.pointer_obj_time = None
        else:
            return False

        return self.handle_keysym(keysym)

    def global_binding(self, key, action, helptext=''):
        self.global_mode.bind(key, action, helptext)

    def set_major_mode(self, mode):
        if isinstance(self.major_mode, InputMode):
            self.major_mode.disable()
        self.major_mode = mode
        mode.enable()
        self.window.display_bindings()

    def mode_enabled(self, mode_type):
        if (
            isinstance(self.global_mode, mode_type)
            or isinstance(self.major_mode, mode_type)
            or any(isinstance(m, mode_type) for m in self.minor_modes)
        ):
            return True
        return False

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

    def _wrap_handler(self, func, mode):
        def inner(*args, **kwargs):
            if len(inspect.signature(func).parameters):
                return func(mode)
            return func()
        return inner

    def get_handlers(self, keysym):
        handlers = []
        if keysym is not None:
            # check minor modes first
            for minor in self.minor_modes:
                handler = minor.lookup(keysym)
                if handler is not None:
                    handlers.append(self._wrap_handler(handler[0], minor))

            # then major mode
            if self.major_mode is not None and self.major_mode.enabled:
                handler = self.major_mode.lookup(keysym)
                if handler is not None:
                    handlers.append(self._wrap_handler(handler[0], self.major_mode))

            # then global
            handler = self.global_mode.lookup(keysym)
            if handler is not None:
                handlers.append(self._wrap_handler(handler[0], self.global_mode))

        return handlers
