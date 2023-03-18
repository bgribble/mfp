#! /usr/bin/env python
'''
console.py -- Python read-eval-print console for MFP

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from threading import Thread, Lock, Condition
import time
from mfp.gui_main import MFPGUI
from gi.repository import Gtk

from .key_defs import *  # noqa

DEFAULT_PROMPT = ">>> "
DEFAULT_CONTINUE = "... "


class ConsoleMgr (Thread):
    def __init__(self, banner, textview):
        self.quitreq = False
        self.lock = Lock()
        self.condition = Condition(self.lock)
        self.textview = textview
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

        Thread.__init__(self)

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

        cursiter = self.textbuffer.get_iter_at_line_offset(lastline,
                                                           len(self.last_ps) + self.cursor_pos)
        self.textbuffer.place_cursor(cursiter)
        self.scroll_to_end()

    def line_ready(self):
        self.ready = True
        with self.lock:
            self.condition.notify()

    def readline(self):
        '''
        Try to return a complete line, or None if one is not ready
        '''

        def try_once():
            if self.ready:
                buf = self.linebuf
                self.linebuf = ''
                self.cursor_pos = 0
                self.ready = False
                return buf
            else:
                return None

        with self.lock:
            buf = try_once()
            if buf is not None:
                return buf
            self.condition.wait(0.2)
            buf = try_once()
            if buf is not None:
                return buf

    def append(self, msg):
        iterator = self.textbuffer.get_end_iter()
        self.textbuffer.insert(iterator, msg, -1)
        self.scroll_to_end()

    def run(self):
        time.sleep(0.1)
        continued = False

        while not self.quitreq:
            # write the line prompt
            if not continued:
                self.last_ps = self.ps1
                MFPGUI().clutter_do(lambda: self.append(self.ps1))
            else:
                self.last_ps = self.ps2
                MFPGUI().clutter_do(lambda: self.append(self.ps2))

            # wait for input, possibly quitting if needed
            cmd = None
            while cmd is None and not self.quitreq:
                cmd = self.readline()

            if not self.quitreq:
                self.continue_buffer += '\n' + cmd
                resp = self.evaluate(self.continue_buffer)
                continued = resp.continued
                if not continued:
                    self.continue_buffer = ''
                    MFPGUI().clutter_do(lambda: self.append(resp.value + '\n'))

    def evaluate(self, cmd):
        # returns True if a syntactically complete but partial line
        # was entered, so we can display a continuation prompt

        # returns False if an incorrect or complete and correct
        # expression was entered.

        return MFPGUI().mfp.console_eval.sync(cmd)

    def finish(self):
        self.quitreq = True
        try:
            self.join()
        except Exception:
            pass
