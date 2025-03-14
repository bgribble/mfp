"""
clutter/text_widget.py -- backend implementation of TextWidget for Clutter
"""

from gi.repository import Clutter
from mfp import log
from mfp.gui_main import MFPGUI
from mfp.gui.base_element import BaseElement

from ..text_widget import TextWidget, TextWidgetImpl
from .app_window import ClutterAppWindowImpl
from .event import repeat_event


class ClutterTextWidgetImpl(TextWidget, TextWidgetImpl):
    backend_name = "clutter"
    blink_cursor = True

    def __init__(self, container):
        super().__init__()
        self.container = container
        self.parent = None
        if isinstance(self.container, BaseElement):
            if hasattr(self.container, 'group'):
                self.parent = self.container.group
            else:
                self.parent = self.container.backend.group
        elif isinstance(self.container, ClutterAppWindowImpl):
            self.parent = self.container.container

        self.label = Clutter.Text()
        self.last_text = ""
        self.parent.add_actor(self.label)

        if hasattr(self.container, 'app_window'):
            window = self.container.app_window
            if hasattr(window, 'wrapper'):
                window = window.wrapper

            window.event_sources[self.label] = self.container

        self.key_press_handler_id = None
        self.edit_mode = None

        # repeat the Clutter signals to MFP signals on the TextWidget
        self.label.connect("activate", repeat_event(self, "activate"))
        self.label.connect("text-changed", self.text_changed_cb)
        self.label.connect("key-focus-out", repeat_event(self, "key-focus-out"))
        self.label.connect("key-focus-in", repeat_event(self, "key-focus-in"))

    def text_changed_cb(self, widget):
        new_text = self.label.get_text() or ""
        old_text = self.last_text
        self.last_text = new_text
        MFPGUI().async_task(self.signal_emit("text-changed", old_text, new_text))

    async def delete(self):
        if self.label:
            if (
                hasattr(self.container, 'app_window')
                and self.label in self.container.app_window.event_sources
            ):
                del self.container.app_window.event_sources[self.label]

            self.label.destroy()
            self.label = None

    def grab_focus(self):
        return self.label.grab_key_focus() if self.label else None

    def show(self):
        return self.parent.add_actor(self.label)

    def hide(self):
        return self.parent.remove_actor(self.label)

    def get_width(self):
        if not self.label:
            return
        return self.label.get_width()

    def get_height(self):
        if not self.label:
            return
        return self.label.get_height()

    def get_position(self):
        if not self.label:
            return
        return self.label.get_position()

    def set_position(self, x_pos, y_pos):
        if not self.label:
            return
        return self.label.set_position(x_pos, y_pos)

    def set_activatable(self, val):
        if not self.label:
            return
        return self.label.set_activatable(val)

    def set_single_line_mode(self, val):
        if not self.label:
            return
        return self.label.set_single_line_mode(val)

    def get_cursor_position(self):
        if not self.label:
            return
        return self.label.get_cursor_position()

    def set_cursor_position(self, pos):
        if not self.label:
            return
        return self.label.set_cursor_position(pos) if self.label else None

    def set_cursor_visible(self, visible):
        if not self.label:
            return
        return self.label.set_cursor_visible(visible) if self.label else None

    def set_cursor_color(self, color):
        if not self.label:
            return
        return self.label.set_cursor_color(color)

    def get_text(self):
        if not self.label:
            return
        return self.label.get_text()

    def set_text(self, text):
        if not self.label:
            return
        return self.label.set_text(text) if self.label else None

    def set_markup(self, text):
        if not self.label:
            return
        return self.label.set_markup(text)

    def set_reactive(self, is_reactive):
        if not self.label:
            return
        return self.label.set_reactive(is_reactive)

    def set_color(self, color):
        if not self.label:
            return
        return self.label.set_color(color)

    def set_font_name(self, font_name):
        if not self.label:
            return
        return self.label.set_font_name(font_name)

    def get_property(self, propname):
        if not self.label:
            return
        return self.label.get_property(propname)

    def set_use_markup(self, use_markup):
        if not self.label:
            return
        return self.label.set_use_markup(use_markup) if self.label else None

    def set_selection(self, start, end):
        if not self.label:
            return
        return self.label.set_selection(start, end)
