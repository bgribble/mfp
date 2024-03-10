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

        self.append(banner + '\n')

    def button_pressed(self, *args):
        # ignore pesky mousing
        return True

    def key_pressed(self, widget, event):
        if event.keyval == KEY_ENTER:
            self.append("\n")
            stripped_buf = self.linebuf.strip()
            if (
                len(stripped_buf)
                and (len(self.history) == 0 or stripped_buf != self.history[0])
            ):
                self.history[:0] = [self.linebuf]
                self.history_pos = -1
            self.line_ready()
            return True
        if event.keyval == KEY_BKSP:
            if self.cursor_pos > 0:
                self.linebuf = (
                    self.linebuf[:self.cursor_pos - 1] + self.linebuf[self.cursor_pos:])
                self.cursor_pos -= 1
                self.redisplay()
            return True
        if (event.keyval == KEY_DEL or event.string == CTRL_D):
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
        if event.string == CTRL_A:
            self.cursor_pos = 0
            self.redisplay()
            return True
        if event.string == CTRL_E:
            self.cursor_pos = len(self.linebuf)
            self.redisplay()
        if event.string == CTRL_K:
            self.linebuf = self.linebuf[:self.cursor_pos]
            self.redisplay()
        if len(event.string) > 0:
            if ord(event.string[0]) < 32:
                return True
            # print event.string, event.keyval, event.get_keycode()
            self.linebuf = (
                self.linebuf[:self.cursor_pos]
                + event.string
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
