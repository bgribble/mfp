"""
text_widget.py -- wrapper around text widget for backend independence

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from abc import ABC, abstractmethod
from mfp.utils import SignalMixin
from .backend_interfaces import BackendInterface
from ..gui_main import MFPGUI


class TextWidget(SignalMixin):
    """
    TextWidget: A wrapper around the backend's editable label

    Uses simple markup to style text, just using Pango for
    the Clutter backend and emulating it in others
    """
    def __init__(self):
        super().__init__()

        self.editable = False

    def set_editable(self, val):
        self.editable = val

    @classmethod
    def get_factory(cls):
        return TextWidgetImpl.get_backend(MFPGUI().appwin.backend_name)

    @classmethod
    def build(cls, *args, **kwargs):
        return cls.get_factory()(*args, **kwargs)


class TextWidgetImpl(ABC, BackendInterface):
    @abstractmethod
    def set_single_line_mode(self, val):
        pass

    @abstractmethod
    def set_activatable(self, val):
        pass

    @abstractmethod
    def get_cursor_position(self):
        pass

    @abstractmethod
    def set_cursor_position(self, pos):
        pass

    @abstractmethod
    def set_cursor_visible(self, visible):
        pass

    @abstractmethod
    def set_cursor_color(self, color):
        pass

    @abstractmethod
    def grab_focus(self):
        pass

    @abstractmethod
    def hide(self):
        pass

    @abstractmethod
    def show(self):
        pass

    @abstractmethod
    def get_width(self):
        pass

    @abstractmethod
    def get_height(self):
        pass

    @abstractmethod
    def get_position(self):
        pass

    @abstractmethod
    def set_position(self, x_pos, y_pos):
        pass

    @abstractmethod
    def get_text(self):
        pass

    @abstractmethod
    def set_text(self, text):
        pass

    @abstractmethod
    def set_markup(self, text):
        pass

    @abstractmethod
    def set_reactive(self, is_reactive):
        pass

    @abstractmethod
    def set_color(self, color):
        pass

    @abstractmethod
    def set_font_name(self, font_name):
        pass

    @abstractmethod
    def get_property(self, propname):
        pass

    @abstractmethod
    def set_use_markup(self, use_markup):
        pass

    @abstractmethod
    def set_selection(self, start, end):
        pass
