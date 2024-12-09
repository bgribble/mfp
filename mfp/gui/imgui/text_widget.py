"""
imgui/text_widget.py -- backend implementation of TextWidget for Imgui
"""

import re
from imgui_bundle import imgui
from imgui_bundle import imgui_node_editor as nedit
from imgui_bundle import imgui_md as markdown

from mfp import log
from mfp.gui_main import MFPGUI
from mfp.gui.colordb import ColorDB
from ..text_widget import TextWidget, TextWidgetImpl


class ImguiTextWidgetImpl(TextWidget, TextWidgetImpl):
    backend_name = "imgui"
    blink_cursor = False

    imgui_currently_rendering = None
    imgui_font_atlas = {}
    imgui_font_current = None

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
        self.cursor_color = ColorDB().find('default-cursor-color')

        self.visible = True
        self.use_markup = False

        # cached transformed text
        self.transform_in = None
        self.transform_out = None

    def set_editable(self, value):
        super().set_editable(value)
        if value:
            nedit.enable_shortcuts(False)
        else:
            nedit.enable_shortcuts(True)

    @classmethod
    def markdown_div_callback(cls, div_class, is_opening_div):
        classes = div_class.split(' ')
        sizes = {
            "size-x-small": 8.0,
            "size-small": 12.0,
            "size-normal": 16.0,
            "size-large": 20.0,
            "size-x-large": 24.0,
            "size-xx-large": 28.0,
        }
        current_font = imgui.get_current_context().font
        current_font_key = next(
            (key for key, value in cls.imgui_font_atlas.items() if value == current_font),
            "unnamed__regular__16.0"
        )

        font_key_stack = [current_font_key]

        for c in classes:
            font_key = font_key_stack[-1]
            if c in sizes:
                font_base = '__'.join(font_key.split('__')[:-1])
                new_font_key = f"{font_base}__{sizes[c]}"
                new_font = cls.imgui_font_atlas.get(
                    new_font_key, None
                )
                if new_font:
                    if is_opening_div:
                        font_key_stack.append(new_font_key)
                        imgui.push_font(new_font)
                    else:
                        font_key_stack = font_key_stack[:-1]
                        imgui.pop_font()

            if c in ['bold', 'italic', 'bolditalic', 'regular']:
                font_name, font_weight, font_size = font_key.split('__')
                if c in ["regular", "bolditalic"]:
                    font_weight = c
                elif font_weight == 'bold' and c == 'italic':
                    font_weight = 'bolditalic'
                elif font_weight == 'italic' and c == 'bold':
                    font_weight = 'bolditalic'
                else:
                    font_weight=c
                new_font_key = '__'.join([font_name, font_weight, font_size])
                new_font = cls.imgui_font_atlas.get(
                    new_font_key, None
                )
                if new_font:
                    if is_opening_div:
                        font_key_stack.append(new_font_key)
                        imgui.push_font(new_font)
                    else:
                        font_key_stack = font_key_stack[:-1]
                        imgui.pop_font()

            if c.startswith('color'):
                colorparts = c.split('-')
                if len(colorparts) == 2:
                    hexcolor = colorparts[1]
                    r = int(hexcolor[0:2], 16) if len(hexcolor) >= 2 else 255
                    g = int(hexcolor[2:4], 16) if len(hexcolor) >= 4 else 255
                    b = int(hexcolor[4:6], 16) if len(hexcolor) >= 6 else 255
                    a = int(hexcolor[6:8], 16) if len(hexcolor) >= 8 else 255

                    if is_opening_div:
                        imgui.push_style_color(
                            imgui.Col_.text, [r, g, b, a]
                        )
                    else:
                        imgui.pop_style_color()

    def simple_wrap(self, text, max_columns):
        lines = []
        line_words = []
        line_col = 0
        for line in text.split('\n'):
            if line == '':
                lines.append(line)
                continue
            for word_num, word in enumerate(line.split()):
                if not word_num or (line_col + len(word) < max_columns):
                    line_words.append(word)
                    line_col += len(word) + 1

                    if line_col >= max_columns:
                        lines.append(" ".join(line_words))
                        line_col = 0
                        line_words = []
                else:
                    lines.append(" ".join(line_words))
                    line_col = len(word)
                    line_words = [word]

            if len(line_words) > 0:
                lines.append(" ".join(line_words))
                line_col = 0
                line_words = []

        return "\n".join(lines)

    def split_blocks(self, md_text):
        """
        we want to split out code blocks, since we don't do anything to
        their content

        code blocks are either ``` - delimited or start with exactly
        4 leading spaces and run until there are fewer than 4 leading
        spaces
        """
        match_pos = 0
        blocks = []
        for match in re.finditer(
            r'(^```(.*?)\n```)|(^    [^ ].*?\n(^    .*?\n)+)',
            md_text,
            re.MULTILINE | re.DOTALL
        ):
            if match_pos < match.span()[0]:
                blocks.append((False, md_text[match_pos:match.span()[0]]))
            codeblock = match.group(0)
            blocks.append((True, codeblock))
            match_pos = match.span()[1]

        if match_pos != len(md_text):
            blocks.append((False, md_text[match_pos:]))

        return blocks

    def transform_codeblock(self, md_text):
        """
        code blocks are not working right now, so just change to a
        series of `escaped` lines
        """
        code_lines = []
        fenced = md_text.startswith('```')

        for line_num, line in enumerate(md_text.split('\n')):
            if fenced:
                if line_num == 0:
                    continue
                line = f"`{re.sub('```', '', line)}`"
            else:
                line = f"`{re.sub('^    ', '', line)}`"

            if line == "``":
                code_lines.append('')
            else:
                code_lines.append(line)

        if code_lines[-1] == '':
            code_lines = code_lines[:-1]

        return '\n<br>'.join(code_lines)

    def transform_md(self, md_text):
        # pango/html escape char replacements
        md_text = re.sub('&lt;', '<', md_text)
        md_text = re.sub('&gt;', '>', md_text)
        md_text = re.sub(
            '&#([0-9]*);',
            lambda match: chr(int(match.group(1))),
            md_text)

        # exactly 4 spaces is a code block; 3 or 5 is a misguided blockquote
        md_text = re.sub(
            r'^   ([^ ]|  +)',
            lambda match: ('> ' + (match.group(1) if len(match.group(1)) == 1 else '')),
            md_text,
            flags=re.MULTILINE
        )
        # add a newline before a block quote
        md_text = re.sub(
            '^([^>][^\n]*?)\n> ',
            '\\1\n\n> ',
            md_text,
            flags=re.MULTILINE
        )
        # add linebreaks between lines
        md_text = re.sub(
            '^(> [^\n]*?)(?<!<br>)\n> ',
            '\\1<br>\n> ',
            md_text,
            flags=re.MULTILINE
        )
        # twice because sequential lines will overlap, and sub only gets non-overlapping
        md_text = re.sub(
            '^(> [^\n]*?)(?<!<br>)\n> ',
            '\\1<br>\n> ',
            md_text,
            flags=re.MULTILINE
        )

        # single newlines with non-newline after are part of the
        # preceding paragraph, so replace newline with space
        md_text = re.sub(
            '([^\n])\n([^>\n])',
            r'\1 \2',
            md_text,
            flags=re.MULTILINE
        )

        # short circuit on tag changes
        if '<' not in md_text:
            self.transform_out = md_text
            return md_text

        # <span size="smol">text</span> --> <div class="size-smol">text</div>
        md_text = re.sub(
            r'<span size="([^"]*?)">(.*?)</span>',
            r'<div class="size-\1">\2</div>',
            md_text,
            flags=re.DOTALL
        )

        # <b>text</b> --> <div class="bold">text</div>
        md_text = re.sub(r'<b>(.*?)</b>', r'<div class="bold">\1</div>', md_text, flags=re.DOTALL)
        md_text = re.sub(r'<em>(.*?)</em>', r'<div class="bold">\1</div>', md_text, flags=re.DOTALL)

        # <i>text</i> --> *text*
        md_text = re.sub(r'<i>(.*?)</i>', r'<div class="italic">\1</div>', md_text, flags=re.DOTALL)

        # <tt>text</tt> --> `text`
        md_text = re.sub(r'<tt>(.*?)</tt>', r'`\1`', md_text, flags=re.DOTALL)

        # <small>text</small> --> <div class="size-small">text</div>
        md_text = re.sub(
            r'<small>(.*?)</small>',
            r'<div class="size-small">\1</div>',
            md_text,
            flags=re.DOTALL
        )

        # for some reason imgui_md doesn't parse divs that start at the
        # beginning of the line. luckily it also doesn't render &nbsp;
        md_text = re.sub(r'^( *)<', r'\1&nbsp;<', md_text, flags=re.MULTILINE)

        return md_text

    def render(self, wrap_width=None):
        extra_bit = ''
        if self.multiline and self.text[:-1] == '\n':
            extra_bit = ' '

        if type(self).imgui_font_atlas == {}:
            font_styles = [
                'regular', 'bold', 'italic', 'bolditalic'
            ]
            atlas = imgui.get_io().fonts
            fonts = atlas.fonts
            font_size = None
            font_index = 0
            for f in fonts:
                if f.font_size != font_size:
                    font_index = 0
                    font_size = f.font_size
                if font_index >= len(font_styles):
                    continue

                style = font_styles[font_index]
                fkey = f"{f.get_debug_name() or 'unnamed'}__{style}__{f.font_size}"
                type(self).imgui_font_atlas[fkey] = f
                font_index += 1

        type(self).imgui_currently_rendering = self

        imgui.begin_group()
        if self.markdown_text and self.use_markup:
            # imgui_md draws underlines for H1 and H2 that need to
            # be clipped
            my_x = self.position_x + self.container.position_x
            my_y = self.position_y + self.container.position_y - 2
            draw_list = imgui.get_window_draw_list()
            draw_list.push_clip_rect(
                (my_x, my_y),
                (my_x + self.width, my_y + self.height + 4),
                True
            )

            # sometimes imgui_md doesn't call the div-callback
            # so we need to be defensive about the font stack
            context = imgui.get_current_context()
            font_depth_before = len(context.font_stack)

            # transform converts to better-renderable form
            # and also has some Pango compatibility shims
            if self.transform_in == self.markdown_text:
                md_text = self.transform_out
            else:
                self.transform_in = self.markdown_text
                blocks = self.split_blocks(self.markdown_text)
                transformed_blocks = []
                for is_codeblock, b in blocks:
                    if is_codeblock:
                        transformed_blocks.append(self.transform_codeblock(b))
                    else:
                        transformed_blocks.append(self.transform_md(b))
                md_text = '\n'.join(transformed_blocks)
                self.transform_out = md_text

            markdown.render(md_text)

            # check for stray fonts on the stack and get rid of them
            context = imgui.get_current_context()
            draw_list.pop_clip_rect()
            font_depth_after = len(context.font_stack)

            if font_depth_before != font_depth_after:
                log.debug("[text] Warning: font stack is messed up, doing my best")
            for _ in range(font_depth_before, font_depth_after):
                imgui.pop_font()
        else:
            label_text = self.text
            if self.multiline and wrap_width:
                label_text = self.simple_wrap(self.text, int(wrap_width / self.font_width))

            if self.font_color:
                imgui.text_colored(
                    self.font_color.to_rgbaf(),
                    label_text + extra_bit
                )
            else:
                imgui.text(label_text + extra_bit)

        self.font_width, self.font_height = imgui.calc_text_size("M")
        imgui.end_group()

        w, h = imgui.get_item_rect_size()
        left_x, top_y = imgui.get_item_rect_min()

        self.width = w
        self.height = h

        if not self.editable:
            return

        draw_list = imgui.get_window_draw_list()
        lines = label_text.split("\n")
        line_start_pos = 0

        for line in lines:
            line_end_pos = line_start_pos + len(line)
            if self.selection_start <= line_end_pos and self.selection_end >= line_start_pos:
                box_start = max(0, self.selection_start - line_start_pos)
                box_end = min(len(line), self.selection_end - line_start_pos)

                # draw cursor
                draw_list.add_rect_filled(
                    (left_x + box_start * self.font_width - 1, top_y),
                    (left_x + box_end * self.font_width + 1, top_y + self.font_height + 2),
                    ColorDB().backend.im_col32(self.cursor_color)
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
