from imgui_bundle import imgui

from mfp.utils import SignalMixin
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
        imgui.text(self.textbuffer.buffer + self.linebuf)

    def handle_event(self, target, event):
        log.debug(f"[console] got {target} {event}")
        if not isinstance(event, KeyPressEvent):
            return

        if event.keyval == KEY_ENTER:
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
        if event.keyval == KEY_BKSP:
            if self.cursor_pos > 0:
                self.linebuf = (
                    self.linebuf[:self.cursor_pos - 1] + self.linebuf[self.cursor_pos:])
                self.cursor_pos -= 1
                self.redisplay()
            return True
        if (event.keyval == KEY_DEL or event.unicode == CTRL_D):
            if self.cursor_pos < len(self.linebuf):
                self.linebuf = (
                    self.linebuf[:self.cursor_pos] + self.linebuf[self.cursor_pos + 1:])
                self.redisplay()
            return True
        if event.keyval == KEY_UP:
            if self.history_pos >= -1 and self.history_pos < len(self.history) - 1:
                if self.history_pos == -1:
                    self.history_linebuf = self.linebuf
                self.history_pos += 1
                self.linebuf = self.history[self.history_pos]
                self.cursor_pos = len(self.linebuf)
                self.redisplay()
            return True
        if event.keyval == KEY_DN:
            if self.history_pos > -1 and self.history_pos < len(self.history):
                self.history_pos -= 1
                if self.history_pos == -1:
                    self.linebuf = self.history_linebuf
                else:
                    self.linebuf = self.history[self.history_pos]
                self.cursor_pos = len(self.linebuf)
                self.redisplay()
            return True
        if event.keyval == KEY_LEFT:
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
            self.redisplay()
            return True
        if event.keyval == KEY_RIGHT:
            if self.cursor_pos < len(self.linebuf):
                self.cursor_pos += 1
            self.redisplay()
            return True
        if event.unicode == CTRL_A:
            self.cursor_pos = 0
            self.redisplay()
            return True
        if event.unicode == CTRL_E:
            self.cursor_pos = len(self.linebuf)
            self.redisplay()
        if event.unicode == CTRL_K:
            self.linebuf = self.linebuf[:self.cursor_pos]
            self.redisplay()
        if event.unicode and len(event.unicode) > 0:
            if ord(event.unicode[0]) < 32:
                return True
            # print event.unicode, event.keyval, event.get_keycode()
            self.linebuf = (
                self.linebuf[:self.cursor_pos]
                + event.unicode
                + self.linebuf[self.cursor_pos:]
            )
            self.cursor_pos += 1
            self.redisplay()
            return True

        return False

    def scroll_to_end(self):
        return True

    def redisplay(self):
        return True

    def append(self, text):
        self.textbuffer.append(text)
