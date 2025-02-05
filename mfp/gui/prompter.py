#! /usr/bin/env python
'''
prompter.py -- Prompted input manager for MFP patch window

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''
import inspect
from .modes.label_edit import LabelEditMode
from mfp import log
from mfp.trie import Trie


class Prompter (object):
    def __init__(self, window, label, completions=None):
        self.window = window
        self.queue = []
        self.current_prompt = None
        self.current_callback = None
        self.callback_incremental = False
        self.mode = None
        self.label = label
        self.completions = Trie()
        self.history = Trie()
        self.completions.populate(completions or [])

    async def get_input(self, prompt, callback, default, filename, incremental=False, space=True):
        if self.mode is None:
            await self._begin(prompt, callback, default, filename, incremental, space)
        else:
            self.queue.append([prompt, callback, default, filename, incremental, space])

    async def _begin(self, prompt, callback, default, filename, incremental, space):
        self.current_prompt = prompt
        self.current_callback = callback
        self.callback_incremental = incremental
        self.window.cmd_set_prompt(prompt, default, filename=filename, space=space)
        self.mode = LabelEditMode(
            self.window, self, self.label,
            mode_desc="Command input",
            completions=self.completions,
            history=self.history
        )
        await self.mode.setup()
        self.window.input_mgr.enable_minor_mode(self.mode)

    async def label_edit_start(self):
        pass

    async def label_edit_changed(self, widget, text):
        if self.callback_incremental and self.current_callback:
            try:
                rv = self.current_callback(text, incremental=True)
                if inspect.isawaitable(rv):
                    await rv
            except Exception as e:
                log.debug_traceback(e)

    async def label_edit_finish(self, widget, text, aborted=False):
        self.window.input_mgr.disable_minor_mode(self.mode)
        if text and not aborted:
            self.history.populate([text])

        if self.current_callback:
            try:
                incr = {}
                if self.callback_incremental:
                    incr = dict(incremental=False)

                cb_text = text
                if aborted:
                    cb_text = None

                rv = self.current_callback(cb_text, **incr)
                if inspect.isawaitable(rv):
                    await rv
            except Exception as e:
                log.debug_traceback(e)

    async def end_edit(self):
        if self.mode:
            self.window.input_mgr.disable_minor_mode(self.mode)
            self.mode = None
        self.label.text = ''
        self.window.cmd_set_prompt(None)
        if len(self.queue) > 0:
            nextitem = self.queue[0]
            self.queue = self.queue[1:]
            await self._begin(*nextitem)
