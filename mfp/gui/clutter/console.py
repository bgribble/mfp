
from gi.repository import Gtk
from ..backend_interfaces import ConsoleManagerBackend

from .key_defs import *  # noqa


class ClutterConsoleManagerBackend(ConsoleManagerBackend):
    backend_name = "clutter"

    def __init__(self, console_manager):
        self.console_manager = console_manager

        self.textview = console_manager.app_window.backend.console_view
        self.textbuffer = self.textview.get_buffer()

        self.textview.connect('key-press-event', self.key_pressed)
        self.textview.connect('button-press-event', self.button_pressed)

        super().__init__(console_manager)

    def button_pressed(self, *args):
        # ignore pesky mousing
        self.textview.grab_focus()
        return True

    def key_pressed(self, widget, event):
        if event.keyval == KEY_ENTER:
            self.console_manager.append("\n")
            stripped_buf = self.console_manager.linebuf.strip()
            if (
                len(stripped_buf)
                and (not len(self.console_manager.history) or stripped_buf != self.console_manager.history[0])
            ):
                self.console_manager.history[:0] = [self.console_manager.linebuf]
                self.console_manager.history_pos = -1
            self.console_manager.line_ready()
            return True
        elif event.keyval == KEY_BKSP:
            if self.console_manager.cursor_pos > 0:
                self.console_manager.linebuf = (
                    self.console_manager.linebuf[:self.console_manager.cursor_pos - 1] + self.console_manager.linebuf[self.console_manager.cursor_pos:])
                self.console_manager.cursor_pos -= 1
                self.console_manager.redisplay()
            return True
        elif (event.keyval == KEY_DEL or event.string == CTRL_D):
            if self.console_manager.cursor_pos < len(self.console_manager.linebuf):
                self.console_manager.linebuf = (
                    self.console_manager.linebuf[:self.console_manager.cursor_pos] + self.console_manager.linebuf[self.console_manager.cursor_pos + 1:])
                self.console_manager.redisplay()
            return True
        elif event.keyval == KEY_UP:
            if self.console_manager.history_pos >= -1 and self.console_manager.history_pos < len(self.console_manager.history) - 1:
                if self.console_manager.history_pos == -1:
                    self.console_manager.history_linebuf = self.console_manager.linebuf
                self.console_manager.history_pos += 1
                self.console_manager.linebuf = self.console_manager.history[self.console_manager.history_pos]
                self.console_manager.cursor_pos = len(self.console_manager.linebuf)
                self.console_manager.redisplay()
            return True
        elif event.keyval == KEY_DN:
            if self.console_manager.history_pos > -1 and self.console_manager.history_pos < len(self.console_manager.history):
                self.console_manager.history_pos -= 1
                if self.console_manager.history_pos == -1:
                    self.console_manager.linebuf = self.console_manager.history_linebuf
                else:
                    self.console_manager.linebuf = self.console_manager.history[self.console_manager.history_pos]
                self.console_manager.cursor_pos = len(self.console_manager.linebuf)
                self.console_manager.redisplay()
            return True
        elif event.keyval == KEY_LEFT:
            if self.console_manager.cursor_pos > 0:
                self.console_manager.cursor_pos -= 1
            self.console_manager.redisplay()
            return True
        elif event.keyval == KEY_RIGHT:
            if self.console_manager.cursor_pos < len(self.console_manager.linebuf):
                self.console_manager.cursor_pos += 1
            self.console_manager.redisplay()
            return True
        elif event.string == CTRL_A:
            self.console_manager.cursor_pos = 0
            self.console_manager.redisplay()
            return True
        elif event.string == CTRL_E:
            self.console_manager.cursor_pos = len(self.console_manager.linebuf)
            self.console_manager.redisplay()
        elif event.string == CTRL_K:
            self.console_manager.linebuf = self.console_manager.linebuf[:self.console_manager.cursor_pos]
            self.console_manager.redisplay()
        elif len(event.string) > 0:
            if ord(event.string[0]) < 32:
                return True
            # print event.string, event.keyval, event.get_keycode()
            self.console_manager.linebuf = (
                self.console_manager.linebuf[:self.console_manager.cursor_pos]
                + event.string
                + self.console_manager.linebuf[self.console_manager.cursor_pos:]
            )
            self.console_manager.cursor_pos += 1
            self.console_manager.redisplay()
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
        start_iter = self.textbuffer.get_iter_at_line_offset(lastline, len(self.console_manager.last_ps))
        end_iter = self.textbuffer.get_end_iter()
        self.textbuffer.delete(start_iter, end_iter)
        end_iter = self.textbuffer.get_end_iter()
        self.textbuffer.insert(end_iter, self.console_manager.linebuf, -1)
        end_iter = self.textbuffer.get_end_iter()

        cursiter = self.textbuffer.get_iter_at_line_offset(
            lastline, len(self.console_manager.last_ps) + self.console_manager.cursor_pos
        )
        self.textbuffer.place_cursor(cursiter)
        self.scroll_to_end()

    def append(self, msg):
        iterator = self.textbuffer.get_end_iter()
        self.textbuffer.insert(iterator, msg, -1)
        self.scroll_to_end()
