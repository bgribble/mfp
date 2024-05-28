"""
imgui/text_widget.py -- backend implementation of TextWidget for Imgui
"""

from imgui_bundle import imgui

from mfp import log
from ..text_widget import TextWidget, TextWidgetImpl


class ImguiTextWidgetImpl(TextWidget, TextWidgetImpl):
    backend_name = "imgui"

    def __init__(self, container):
        super().__init__()
        self.container = container
        self.parent = None
        self.text = ""
        self.width = 0
        self.height = 0

    def render(self):
        imgui.text(self.text)
        self.width, self.height = imgui.get_item_rect_size()

    def set_single_line_mode(self, val):
        pass

    def set_activatable(self, val):
        pass

    def get_cursor_position(self):
        pass

    def set_cursor_position(self, pos):
        pass

    def set_cursor_visible(self, visible):
        pass

    def set_cursor_color(self, color):
        pass

    def grab_focus(self):
        pass

    def hide(self):
        pass

    def show(self):
        pass

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_position(self):
        pass

    def set_position(self, x_pos, y_pos):
        pass

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text

    def set_markup(self, text):
        self.text = text

    def set_reactive(self, is_reactive):
        pass

    def set_color(self, color):
        pass

    def set_font_name(self, font_name):
        pass

    def get_property(self, propname):
        if hasattr(self, propname):
            return getattr(self, propname)
        return None

    def set_use_markup(self, use_markup):
        pass

    def set_selection(self, start, end):
        pass
