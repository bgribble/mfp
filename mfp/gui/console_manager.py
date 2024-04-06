#! /usr/bin/env python
'''
console.py -- Python read-eval-print console for MFP

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

from abc import ABC, abstractmethod
import asyncio
from mfp.gui_main import MFPGUI
from .backend_interfaces import BackendInterface

DEFAULT_PROMPT = ">>> "
DEFAULT_CONTINUE = "... "


class ConsoleManagerImpl(ABC):
    @abstractmethod
    def scroll_to_end(self):
        pass

    @abstractmethod
    def redisplay(self):
        pass

    @abstractmethod
    def append(self, text):
        pass


class ConsoleManager (BackendInterface):
    def __init__(self, banner, app_window):
        super().__init__()

        self.app_window = app_window

        self.task = None
        self.new_input = asyncio.Event()

        self.linebuf = ''
        self.history_linebuf = ''
        self.history = []
        self.history_pos = -1
        self.cursor_pos = 0
        self.ready = False

        self.ps1 = DEFAULT_PROMPT
        self.ps2 = DEFAULT_CONTINUE
        self.last_ps = self.ps1
        self.continue_buffer = ''

    @classmethod
    def build(cls, *args, **kwargs):
        return cls.get_backend(MFPGUI().backend_name)(*args, **kwargs)

    def line_ready(self):
        self.ready = True
        self.new_input.set()

    async def readline(self):
        '''
        Try to return a complete line, or None if one is not ready
        '''

        def try_once():
            self.new_input.clear()
            if self.ready:
                buf = self.linebuf
                self.linebuf = ''
                self.cursor_pos = 0
                self.ready = False
                return buf
            else:
                return None

        await self.new_input.wait()
        buf = try_once()
        return buf

    def show_prompt(self, prompt):
        self.append(prompt)
        self.last_ps = prompt

    def start(self):
        self.task = MFPGUI().async_task(self.run())

    async def run(self):
        continued = False

        while True:
            # write the line prompt
            if not continued:
                self.show_prompt(self.ps1)
            else:
                self.show_prompt(self.ps2)

            self.redisplay()

            # wait for input
            cmd = None
            while cmd is None:
                cmd = await self.readline()

            self.continue_buffer += '\n' + cmd
            resp = await self.evaluate(self.continue_buffer)
            continued = resp.continued
            if not continued:
                self.continue_buffer = ''
                if resp.value is not None:
                    self.append(resp.value + '\n')

    async def evaluate(self, cmd):
        return await MFPGUI().mfp.console_eval(cmd)

    def finish(self):
        if self.task:
            task = self.task
            self.task = None
            task.cancel()
