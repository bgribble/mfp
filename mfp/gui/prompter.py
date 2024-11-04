#! /usr/bin/env python
'''
prompter.py -- Prompted input manager for MFP patch window

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''
import inspect
import asyncio
from .modes.label_edit import LabelEditMode
from mfp import log

class Prompter (object):
    def __init__(self, window, label):
        self.window = window
        self.queue = []
        self.current_prompt = None
        self.current_callback = None
        self.mode = None
        self.label = label

    async def get_input(self, prompt, callback, default):
        if self.mode is None:
            await self._begin(prompt, callback, default)
        else:
            self.queue.append([prompt, callback, default])

    async def _begin(self, prompt, callback, default):
        self.current_prompt = prompt
        self.current_callback = callback
        self.window.cmd_set_prompt(prompt, default)
        self.mode = LabelEditMode(
            self.window, self, self.label,
            mode_desc="Command input"
        )
        await self.mode.setup()
        self.window.input_mgr.enable_minor_mode(self.mode)

    async def label_edit_start(self):
        pass

    async def label_edit_finish(self, widget, text):
        if self.current_callback:
            try:
                rv = self.current_callback(text)
                if inspect.isawaitable(rv):
                    await rv
            except Exception as e:
                log.error(f"Prompter exception in callback: {e}")

    async def end_edit(self):
        if self.mode:
            self.window.input_mgr.disable_minor_mode(self.mode)
            self.mode = None
        self.label.text = ''
        self.window.cmd_set_prompt(None)
        if len(self.queue):
            nextitem = self.queue[0]
            self.queue = self.queue[1:]
            await self._begin(nextitem[0], nextitem[1], nextitem[2])


