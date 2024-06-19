"""
imgui/text_widget.py -- backend implementation of TextWidget for Imgui
"""

from imgui_bundle import imgui

from mfp import log
from ..text_widget import TextWidget, TextWidgetImpl


class ImguiTextWidgetImpl(TextWidget, TextWidgetImpl):
    backend_name = "imgui"
    blink_cursor = False 

    def __init__(self, container):
        super().__init__()
        self.container = container
        self.parent = None
        self.text = ""
        self.width = 0
        self.height = 0
        self.position_x = 0
        self.position_y = 0
        self.position_set = False
        self.font_width = 6
        self.font_height = 11

        self.multiline = False

        self.selection_start = 0
        self.selection_end = 0

        self.cursor_pos = 0
        self.cursor_visible = False

        self.visible = True

    def render(self):
        # multiline?
        imgui.text(self.text)
        text_width, text_height = imgui.calc_text_size(self.text)

        w, h = imgui.get_item_rect_size()
        left_x, top_y = imgui.get_item_rect_min()

        if len(self.text) > 0:
            self.font_width = text_width / len(self.text)
            self.font_height = text_height
        
        if self.editable:
            draw_list = imgui.get_window_draw_list()

            # draw cursor
            draw_list.add_rect_filled(
                (left_x + self.selection_start * self.font_width, top_y),
                (left_x + self.selection_end * self.font_width + 1.0, top_y + self.font_height),
                imgui.IM_COL32(0, 0, 0, 90) 
            )


    def set_single_line_mode(self, val):
        self.multiline = not val

    def set_activatable(self, val):
        pass

    def get_cursor_position(self):
        return self.cursor_pos

    def set_cursor_position(self, pos):
        self.cursor_pos = pos

    def set_cursor_visible(self, visible):
        self.cursor_visible = visible

    def set_cursor_color(self, color):
        pass

    def grab_focus(self):
        pass

    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def get_position(self):
        return (self.position_x, self.position_y)

    def set_position(self, x_pos, y_pos):
        self.position_x = x_pos
        self.position_y = y_pos

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
        self.selection_start = start
        self.selection_end = end
