"""
clutter/text_widget.py -- backend implementation of TextWidget for Clutter
"""

from gi.repository import Clutter
from mfp.gui_main import MFPGUI
from mfp.gui.base_element import BaseElement

from ..backend_interfaces import TextWidgetBackend
from .app_window import ClutterAppWindowBackend


class ClutterTextWidgetBackend(TextWidgetBackend):
    backend_name = "clutter"

    def __init__(self, owner):
        self.owner = owner

        if isinstance(owner.container, BaseElement):
            self.parent = owner.container.backend.group
        elif isinstance(owner.container, ClutterAppWindowBackend):
            self.parent = owner.container.container

        self.label = Clutter.Text()
        self.parent.add_actor(self.label)

        def signal_repeater(signal_name):
            return lambda *args: MFPGUI().async_task(
                self.owner.signal_emit(signal_name, *args)
            )

        # repeat the Clutter signals to MFP signals on the TextWidget
        self.label.connect("activate", signal_repeater("activate"))
        self.label.connect("text-changed", signal_repeater("text-changed"))
        self.label.connect("key-focus-out", signal_repeater("key-focus-out"))
        self.label.connect("key-focus-in", signal_repeater("key-focus-in"))

        super().__init__(owner)

    def grab_focus(self):
        return self.label.grab_key_focus()

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

    def set_editable(self, val):
        return self.label.set_editable(val)

    def set_single_line_mode(self, val):
        return self.label.set_single_line_mode(val)

    def get_cursor_position(self):
        return self.label.get_cursor_position()

    def set_cursor_position(self, pos):
        return self.label.set_cursor_position(pos)

    def set_cursor_visible(self, visible):
        return self.label.set_cursor_visible(visible)

    def set_cursor_color(self, color):
        return self.label.set_cursor_color(color)

    def get_text(self):
        return self.label.get_text()

    def set_text(self, text):
        return self.label.set_text(text)

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
        return self.label.set_use_markup(use_markup)

    def set_selection(self, start, end):
        return self.label.set_selection(start, end)
