"""
clutter/text_widget.py -- backend implementation of TextWidget for Clutter
"""

from gi.repository import Clutter
from mfp.gui.base_element import BaseElement

from ..text_widget import TextWidget, TextWidgetImpl
from .app_window import ClutterAppWindowBackend
from .event import repeat_event


class ClutterTextWidgetImpl(TextWidget, TextWidgetImpl):
    backend_name = "clutter"

    def __init__(self, container):
        super().__init__()
        self.container = container
        self.parent = None
        if isinstance(self.container, BaseElement):
            if hasattr(self.container, 'group'):
                self.parent = self.container.group
            else:
                self.parent = self.container.backend.group
        elif isinstance(self.container, ClutterAppWindowBackend):
            self.parent = self.container.container

        self.label = Clutter.Text()
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
        self.label.connect("text-changed", repeat_event(self, "text-changed"))
        self.label.connect("key-focus-out", repeat_event(self, "key-focus-out"))
        self.label.connect("key-focus-in", repeat_event(self, "key-focus-in"))

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
        return self.label.get_width()

    def get_height(self):
        return self.label.get_height()

    def get_position(self):
        return self.label.get_position()

    def set_position(self, x_pos, y_pos):
        return self.label.set_position(x_pos, y_pos)

    def set_activatable(self, val):
        return self.label.set_activatable(val)

    def set_single_line_mode(self, val):
        return self.label.set_single_line_mode(val)

    def get_cursor_position(self):
        return self.label.get_cursor_position()

    def set_cursor_position(self, pos):
        return self.label.set_cursor_position(pos) if self.label else None

    def set_cursor_visible(self, visible):
        return self.label.set_cursor_visible(visible) if self.label else None

    def set_cursor_color(self, color):
        return self.label.set_cursor_color(color)

    def get_text(self):
        return self.label.get_text()

    def set_text(self, text):
        return self.label.set_text(text) if self.label else None

    def set_markup(self, text):
        return self.label.set_markup(text)

    def set_reactive(self, is_reactive):
        return self.label.set_reactive(is_reactive)

    def set_color(self, color):
        return self.label.set_color(color)

    def set_font_name(self, font_name):
        return self.label.set_font_name(font_name)

    def get_property(self, propname):
        return self.label.get_property(propname)

    def set_use_markup(self, use_markup):
        return self.label.set_use_markup(use_markup) if self.label else None

    def set_selection(self, start, end):
        return self.label.set_selection(start, end)
