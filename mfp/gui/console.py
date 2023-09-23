#! /usr/bin/env python
'''
console.py -- Python read-eval-print console for MFP

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

import asyncio
from mfp.gui_main import MFPGUI
from gi.repository import Gtk
from mfp import log

from .key_defs import *  # noqa

DEFAULT_PROMPT = ">>> "
DEFAULT_CONTINUE = "... "


class ConsoleMgr:
    def __init__(self, banner, app_window):
        self.task = None
        self.new_input = asyncio.Event()

        # FIXME
        self.textview = app_window.backend.console_view
        self.textbuffer = self.textview.get_buffer()

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

        self.textview.connect('key-press-event', self.key_pressed)
        self.textview.connect('button-press-event', self.button_pressed)

        self.append(banner + '\n')

    def button_pressed(self, *args):
        # ignore pesky mousing
        self.textview.grab_focus()
        return True

    def key_pressed(self, widget, event):
        if event.keyval == KEY_ENTER:
            self.append("\n")
            stripped_buf = self.linebuf.strip()
            if (
                len(stripped_buf)
                and (not len(self.history) or stripped_buf != self.history[0])
            ):
                self.history[:0] = [self.linebuf]
                self.history_pos = -1
            self.line_ready()
            return True
        elif event.keyval == KEY_BKSP:
            if self.cursor_pos > 0:
                self.linebuf = (
                    self.linebuf[:self.cursor_pos - 1] + self.linebuf[self.cursor_pos:])
                self.cursor_pos -= 1
                self.redisplay()
            return True
        elif (event.keyval == KEY_DEL or event.string == CTRL_D):
            if self.cursor_pos < len(self.linebuf):
                self.linebuf = (
                    self.linebuf[:self.cursor_pos] + self.linebuf[self.cursor_pos + 1:])
                self.redisplay()
            return True
        elif event.keyval == KEY_UP:
            if self.history_pos >= -1 and self.history_pos < len(self.history) - 1:
                if self.history_pos == -1:
                    self.history_linebuf = self.linebuf
                self.history_pos += 1
                self.linebuf = self.history[self.history_pos]
                self.cursor_pos = len(self.linebuf)
                self.redisplay()
            return True
        elif event.keyval == KEY_DN:
            if self.history_pos > -1 and self.history_pos < len(self.history):
                self.history_pos -= 1
                if self.history_pos == -1:
                    self.linebuf = self.history_linebuf
                else:
                    self.linebuf = self.history[self.history_pos]
                self.cursor_pos = len(self.linebuf)
                self.redisplay()
            return True
        elif event.keyval == KEY_LEFT:
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
            self.redisplay()
            return True
        elif event.keyval == KEY_RIGHT:
            if self.cursor_pos < len(self.linebuf):
                self.cursor_pos += 1
            self.redisplay()
            return True
        elif event.string == CTRL_A:
            self.cursor_pos = 0
            self.redisplay()
            return True
        elif event.string == CTRL_E:
            self.cursor_pos = len(self.linebuf)
            self.redisplay()
        elif event.string == CTRL_K:
            self.linebuf = self.linebuf[:self.cursor_pos]
            self.redisplay()
        elif len(event.string) > 0:
            if ord(event.string[0]) < 32:
                return True
            # print event.string, event.keyval, event.get_keycode()
            self.linebuf = (self.linebuf[:self.cursor_pos] + event.string
                            + self.linebuf[self.cursor_pos:])
            self.cursor_pos += 1
            self.redisplay()
            return True

        return False

    def scroll_to_end(self):
        iterator = self.textbuffer.get_end_iter()
        mark = self.textbuffer.get_mark("console_mark")
        if mark is None:
            mark = Gtk.TextMark.new("console_mark", False)
            self.textbuffer.add_mark(mark, iterator)
        else:
            self.textbuffer.move_mark(mark, iterator)

        self.textview.scroll_to_mark(mark, 0, True, 1.0, 0.9)

    def redisplay(self):
        lastline = self.textbuffer.get_line_count()-1
        start_iter = self.textbuffer.get_iter_at_line_offset(lastline, len(self.last_ps))
        end_iter = self.textbuffer.get_end_iter()
        self.textbuffer.delete(start_iter, end_iter)
        end_iter = self.textbuffer.get_end_iter()
        self.textbuffer.insert(end_iter, self.linebuf, -1)
        end_iter = self.textbuffer.get_end_iter()

        cursiter = self.textbuffer.get_iter_at_line_offset(
            lastline, len(self.last_ps) + self.cursor_pos
        )
        self.textbuffer.place_cursor(cursiter)
        self.scroll_to_end()

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

    def append(self, msg):
        iterator = self.textbuffer.get_end_iter()
        self.textbuffer.insert(iterator, msg, -1)
        self.scroll_to_end()

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
