"""
imgui/console_manager.py -- REPL handling in imgui backend
"""
from imgui_bundle import imgui

from mfp import log
from ..event import KeyPressEvent
from ..console_manager import ConsoleManager, ConsoleManagerImpl
from ..key_defs import *  # noqa


class TextBuffer:
    def __init__(self, init_value=""):
        self.scroll_pos = 0
        self.edit_pos = 0
        self.buffer = init_value

    def append(self, value):
        self.buffer = self.buffer + value

    def insert(self, value):
        self.buffer = self.buffer[:self.edit_pos] + value + self.buffer[self.edit_pos:]

    def delete_left(self, length):
        self.buffer = self.buffer[:max(0, self.edit_pos-length)] + self.buffer[self.edit_pos:]

    def delete_right(self, length):
        end = min(len(self.buffer), self.edit_pos + length)
        self.buffer = self.buffer[:self.edit_pos] + self.buffer[end:]


class ImguiConsoleManagerImpl(ConsoleManager, ConsoleManagerImpl):
    backend_name = "imgui"

    def __init__(self, banner, app_window):
        super().__init__(banner, app_window)

        self.textbuffer = TextBuffer()
        self.linebuf = ""
        self.append(banner + '\n')

    def render(self, width, height):
        def callback(cb_data):
            bufpos = len(self.textbuffer.buffer) + self.cursor_pos
            cb_data.selection_start = bufpos
            cb_data.selection_end = bufpos
            cb_data.cursor_pos = bufpos
            return 0

        imgui.input_text_multiline(
            'console_input_text',
            self.textbuffer.buffer + self.linebuf,
            (width, height),
            imgui.InputTextFlags_.read_only | imgui.InputTextFlags_.callback_always,
            callback=callback
        )

    def handle_enter(self):
        stripped_buf = self.linebuf.strip()
        if (
            len(stripped_buf)
            and (len(self.history) == 0 or stripped_buf != self.history[0])
        ):
            self.history[:0] = [self.linebuf]
        self.history_pos = -1
        self.append(self.linebuf)
        self.append("\n")
        self.line_ready()
        return True

    def handle_backspace(self):
        if self.cursor_pos > 0:
            self.linebuf = (
                self.linebuf[:self.cursor_pos - 1] + self.linebuf[self.cursor_pos:])
            self.cursor_pos -= 1
            self.redisplay()
        return True

    def handle_delete(self):
        if self.cursor_pos < len(self.linebuf):
            self.linebuf = (
                self.linebuf[:self.cursor_pos] + self.linebuf[self.cursor_pos + 1:])
            self.redisplay()
        return True

    def handle_cursor_up(self):
        if self.history_pos >= -1 and self.history_pos < len(self.history) - 1:
            if self.history_pos == -1:
                self.history_linebuf = self.linebuf
            self.history_pos += 1
            self.linebuf = self.history[self.history_pos]
            self.cursor_pos = len(self.linebuf)
            self.redisplay()
        return True

    def handle_cursor_down(self):
        if self.history_pos > -1 and self.history_pos < len(self.history):
            self.history_pos -= 1
            if self.history_pos == -1:
                self.linebuf = self.history_linebuf
            else:
                self.linebuf = self.history[self.history_pos]
            self.cursor_pos = len(self.linebuf)
            self.redisplay()
        return True

    def handle_cursor_left(self):
        if self.cursor_pos > 0:
            self.cursor_pos -= 1
        self.redisplay()
        return True

    def handle_cursor_right(self):
        if self.cursor_pos < len(self.linebuf):
            self.cursor_pos += 1
        self.redisplay()
        return True

    def handle_start_of_line(self):
        self.cursor_pos = 0
        self.redisplay()
        return True

    def handle_end_of_line(self):
        self.cursor_pos = len(self.linebuf)
        self.redisplay()

    def handle_delete_to_end(self):
        self.linebuf = self.linebuf[:self.cursor_pos]
        self.redisplay()

    def handle_insert_text(self, keysym):
        if len(keysym) > 1:
            return

        self.linebuf = (
            self.linebuf[:self.cursor_pos]
            + keysym
            + self.linebuf[self.cursor_pos:]
        )
        self.cursor_pos += 1
        self.redisplay()

    def scroll_to_end(self):
        return True

    def redisplay(self):
        return True

    def append(self, text):
        self.textbuffer.append(text)
