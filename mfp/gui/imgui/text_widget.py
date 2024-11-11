"""
imgui/text_widget.py -- backend implementation of TextWidget for Imgui
"""

import re
from imgui_bundle import imgui
# from imgui_bundle import imgui_md as markdown

from mfp import log
from mfp.gui_main import MFPGUI
from ..text_widget import TextWidget, TextWidgetImpl


class ImguiTextWidgetImpl(TextWidget, TextWidgetImpl):
    backend_name = "imgui"
    blink_cursor = False

    def __init__(self, container):
        super().__init__()
        self.container = container
        self.parent = None
        self.text = ""
        self.markdown_text = ""
        self.width = 0
        self.height = 0
        self.position_x = 0
        self.position_y = 0
        self.position_set = False
        self.font_width = 6
        self.font_height = 11
        self.font_color = None
        self.multiline = False

        self.selection_start = 0
        self.selection_end = 0

        self.cursor_pos = 0
        self.cursor_visible = False

        self.visible = True
        self.use_markup = False

    def render(self):
        extra_bit = ''
        if self.multiline and self.text[:-1] == '\n':
            extra_bit = ' '

        if self.markdown_text and self.use_markup:
            # markdown.render(self.markdown_text)
            # strip tags
            label_text = re.sub(r'<[^>]*?>', '', self.text)
        else:
            label_text = self.text

        if self.font_color:
            imgui.text_colored(
                self.font_color.to_rgbaf(),
                label_text + extra_bit
            )
        else:
            imgui.text(label_text + extra_bit)

        self.font_width, self.font_height = imgui.calc_text_size("M")

        w, h = imgui.get_item_rect_size()
        left_x, top_y = imgui.get_item_rect_min()

        self.width = w
        self.height = h

        if not self.editable or len(self.text) == 0:
            return

        draw_list = imgui.get_window_draw_list()
        lines = self.text.split("\n")
        line_start_pos = 0

        for line in lines:
            line_end_pos = line_start_pos + len(line)
            if self.selection_start <= line_end_pos and self.selection_end >= line_start_pos:
                box_start = max(0, self.selection_start - line_start_pos)
                box_end = min(len(line), self.selection_end - line_start_pos)

                # draw cursor
                draw_list.add_rect_filled(
                    (left_x + box_start * self.font_width, top_y),
                    (left_x + box_end * self.font_width + 1.0, top_y + self.font_height),
                    imgui.IM_COL32(0, 0, 0, 90)
                )
            line_start_pos += len(line) + 1
            top_y += self.font_height

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
        if self.text != text:
            MFPGUI().async_task(self.signal_emit(
                'text-changed', self.text, text, imgui.calc_text_size(self.text), imgui.calc_text_size(text)
            ))
        self.text = text

    def set_markup(self, text):
        if self.markdown_text != text:
            MFPGUI().async_task(self.signal_emit(
                'text-changed', self.text, text, imgui.calc_text_size(self.markdown_text), imgui.calc_text_size(text)
            ))
        self.markdown_text = text
        self.use_markup = True

    def set_reactive(self, is_reactive):
        pass

    def set_color(self, color):
        self.font_color = color

    def set_font_name(self, font_name):
        pass

    def get_property(self, propname):
        if hasattr(self, propname):
            return getattr(self, propname)
        return None

    def set_use_markup(self, use_markup):
        self.use_markup = use_markup

    def set_selection(self, start, end):
        self.selection_start = start
        self.selection_end = end
