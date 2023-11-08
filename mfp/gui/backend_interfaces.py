"""
backend_interfaces.py -- interface declarations for UI classes

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from abc import ABC, abstractmethod
from ..delegate import DelegateMixin, delegatemethod


class BackendInterface:
    _registry = {}
    _interfaces = {}

    def __init_subclass__(cls, *args, **kwargs):
        if BackendInterface in cls.__bases__:
            BackendInterface._interfaces[cls.__name__] = cls
        else:
            for interface in BackendInterface._interfaces.values():
                if issubclass(cls, interface):
                    be_name = getattr(cls, "backend_name", cls.__name__)
                    interface_registry = BackendInterface._registry.setdefault(interface.__name__, {})
                    interface_registry[be_name] = cls

        super().__init_subclass__(*args, **kwargs)

    def setup(self):
        pass

    @classmethod
    def get_backend(cls, backend_name):
        if cls not in BackendInterface._interfaces.values():
            raise ValueError(f"get_backend: class {cls} is not an interface")

        return BackendInterface._registry.get(cls.__name__, {}).get(backend_name)


class AppWindowBackend(ABC, BackendInterface, DelegateMixin):
    #####################
    # backend control

    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def shutdown(self):
        pass

    @abstractmethod
    def render(self):
        pass

    @abstractmethod
    @delegatemethod
    def grab_focus(self):
        pass

    #####################
    # coordinate transforms and zoom

    @abstractmethod
    def screen_to_canvas(self, x, y):
        pass

    @abstractmethod
    def canvas_to_screen(self, x, y):
        pass

    @abstractmethod
    @delegatemethod
    def rezoom(self):
        pass

    #####################
    # element operations

    @abstractmethod
    def register(self, element):
        pass

    @abstractmethod
    def unregister(self, element):
        pass

    @abstractmethod
    def refresh(self, element):
        pass

    @abstractmethod
    def select(self, element):
        pass

    @abstractmethod
    def unselect(self, element):
        pass

    #####################
    # autoplace

    @abstractmethod
    @delegatemethod
    def show_autoplace_marker(self, x, y):
        pass

    @abstractmethod
    @delegatemethod
    def hide_autoplace_marker(self):
        pass

    #####################
    # HUD/console

    @abstractmethod
    @delegatemethod
    def hud_banner(self, message, display_time=3.0):
        pass

    @abstractmethod
    @delegatemethod
    def hud_write(self, message, display_time=3.0):
        pass

    @abstractmethod
    @delegatemethod
    def hud_set_prompt(self, prompt, default=''):
        pass

    @abstractmethod
    @delegatemethod
    def console_activate(self):
        pass

    #####################
    # clipboard

    @abstractmethod
    @delegatemethod
    def clipboard_cut(self, pointer_pos):
        pass

    @abstractmethod
    @delegatemethod
    def clipboard_copy(self, pointer_pos):
        pass

    @abstractmethod
    @delegatemethod
    def clipboard_paste(self, pointer_pos=None):
        pass

    #####################
    # selection box

    @abstractmethod
    @delegatemethod
    def show_selection_box(self, x0, y0, x1, y1):
        pass

    @abstractmethod
    @delegatemethod
    def hide_selection_box(self):
        pass

    #####################
    # log output

    @abstractmethod
    @delegatemethod
    def log_write(self, message, level):
        pass

    #####################
    # key bindings display

    @abstractmethod
    @delegatemethod
    def display_bindings(self):
        pass


class InputManagerBackend(ABC, BackendInterface, DelegateMixin):
    @abstractmethod
    @delegatemethod
    def handle_event(self, *args):
        pass


class ConsoleManagerBackend(ABC, BackendInterface, DelegateMixin):
    @abstractmethod
    @delegatemethod
    def scroll_to_end(self):
        pass

    @abstractmethod
    @delegatemethod
    def redisplay(self):
        pass

    @abstractmethod
    @delegatemethod
    def append(self, text):
        pass


class LayerBackend(ABC, BackendInterface, DelegateMixin):
    @abstractmethod
    @delegatemethod
    def show(self):
        pass

    @abstractmethod
    @delegatemethod
    def hide(self):
        pass


class TextWidgetBackend(ABC, BackendInterface, DelegateMixin):
    @abstractmethod
    @delegatemethod
    def set_single_line_mode(self, val):
        pass

    @abstractmethod
    @delegatemethod
    def set_activatable(self, val):
        pass

    @abstractmethod
    @delegatemethod
    def get_cursor_position(self):
        pass

    @abstractmethod
    @delegatemethod
    def set_cursor_position(self, pos):
        pass

    @abstractmethod
    @delegatemethod
    def set_cursor_visible(self, pos):
        pass

    @abstractmethod
    @delegatemethod
    def set_cursor_color(self, color):
        pass

    @abstractmethod
    @delegatemethod
    def grab_focus(self):
        pass

    @abstractmethod
    @delegatemethod
    def hide(self):
        pass

    @abstractmethod
    @delegatemethod
    def show(self):
        pass

    @abstractmethod
    @delegatemethod
    def get_width(self):
        pass

    @abstractmethod
    @delegatemethod
    def get_height(self):
        pass

    @abstractmethod
    @delegatemethod
    def get_position(self):
        pass

    @abstractmethod
    @delegatemethod
    def set_position(self, x_pos, y_pos):
        pass

    @abstractmethod
    @delegatemethod
    def get_text(self):
        pass

    @abstractmethod
    @delegatemethod
    def set_text(self, text):
        pass

    @abstractmethod
    @delegatemethod
    def set_markup(self, text):
        pass

    @abstractmethod
    @delegatemethod
    def set_reactive(self, is_reactive):
        pass

    @abstractmethod
    @delegatemethod
    def set_color(self, color):
        pass

    @abstractmethod
    @delegatemethod
    def set_font_name(self, font_name):
        pass

    @abstractmethod
    @delegatemethod
    def get_property(self, propname):
        pass

    @abstractmethod
    @delegatemethod
    def set_use_markup(self, use_markup):
        pass

    @abstractmethod
    @delegatemethod
    def set_selection(self, start, end):
        pass


class BaseElementBackend(ABC, BackendInterface, DelegateMixin):
    @abstractmethod
    @delegatemethod
    def move_to_top(self):
        pass

    @abstractmethod
    @delegatemethod
    def update_badge(self):
        pass

    @abstractmethod
    def draw_ports(self):
        pass

    @abstractmethod
    def hide_ports(self):
        pass

    @abstractmethod
    def set_size(self, width, height):
        pass

    @abstractmethod
    @delegatemethod
    def move(self, x, y):
        pass

    @abstractmethod
    @delegatemethod
    def move_z(self, z):
        pass

class ColorDBBackend(ABC, BackendInterface, DelegateMixin):
    @abstractmethod
    @delegatemethod
    def create_from_rgba(self, red, green, blue, alpha):
        pass

    @abstractmethod
    @delegatemethod
    def create_from_name(self, name):
        pass

    @abstractmethod
    @delegatemethod
    def normalize(self, color):
        pass


