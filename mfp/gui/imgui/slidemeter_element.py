"""
imgui/slidemeter_element.py -- imgui backend for fader and dial elements
"""
import math

from mfp import log
from flopsy import mutates
from imgui_bundle import imgui, imgui_node_editor as nedit, ImVec4
from ..colordb import ColorDB
from ..slidemeter_element import (
    FaderElement,
    FaderElementImpl,
    BarMeterElement,
    BarMeterElementImpl,
    DialElement,
    DialElementImpl,
    #SlideMeterElement,
)
from .base_element import ImguiBaseElementImpl


class rotated:
    def __init__(self, theta=90, origin_x=0.5, origin_y=0.5):
        self.theta = theta
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.initial_drawlist_pos = None

    def rotate_point(self, x, y, about_x, about_y):
        # remember: this is a gfx coord system, Y increases going down!
        delta = math.pi * self.theta / 180.0
        dx = x - about_x
        dy = about_y - y
        orig_angle = math.atan2(dy, dx)
        orig_mag = math.sqrt(dx*dx + dy*dy)
        new_angle = orig_angle + delta
        new_pt = (
            about_x + orig_mag * math.cos(new_angle),
            about_y - orig_mag * math.sin(new_angle)
        )
        return new_pt

    def __enter__(self):
        self.initial_drawlist_pos = imgui.get_window_draw_list().vtx_buffer.size()

    def __exit__(self, exc_type, exc_value, traceback):
        buffer = imgui.get_window_draw_list().vtx_buffer
        final_drawlist_pos = buffer.size()

        if final_drawlist_pos == self.initial_drawlist_pos:
            return

        # find the bounding box
        min_x = None
        min_y = None
        max_x = None
        max_y = None

        for i in range(self.initial_drawlist_pos, final_drawlist_pos):
            pt = buffer[i]
            if min_x is None or pt.pos[0] < min_x:
                min_x = pt.pos[0]
            if min_y is None or pt.pos[1] < min_y:
                min_y = pt.pos[1]
            if max_x is None or pt.pos[0] > max_x:
                max_x = pt.pos[0]
            if max_y is None or pt.pos[1] > max_y:
                max_y = pt.pos[1]

        center_x = min_x + self.origin_x * (max_x - min_x)
        center_y = min_y + self.origin_y * (max_y - min_y)

        for i in range(self.initial_drawlist_pos, final_drawlist_pos):
            pt = buffer[i]
            new_pos = self.rotate_point(
                pt.pos[0], pt.pos[1],
                center_x, center_y
            )
            pt.pos = new_pos


class ImguiSlideMeterElementImpl(ImguiBaseElementImpl):
    backend_name = "imgui"

    def __init__(self, window, x, y):
        super().__init__(window, x, y)
        self.node_id = None
        self.min_width = 10
        self.min_height = 10
        self.width = 24
        self.height = 100
        self.position_set = False
        self.show_scale_set = False

    @mutates('position_x', 'position_y', 'width', 'height')
    def render(self):
        """
        slidemeter element (linear fader and meter)

        rectangular box, slight rounding, no label, draw_list to fill in the
        right portion of the scale
        """
        border_width = 1.25
        border_round = 2

        # style
        padding = self.get_style('padding')
        padding_tpl = (
            padding.get('left', 0),
            padding.get('top', 0),
            padding.get('right', 0),
            padding.get('bottom', 0)
        )
        nedit.push_style_var(nedit.StyleVar.node_rounding, border_round)
        nedit.push_style_var(nedit.StyleVar.node_padding, ImVec4(*padding_tpl))
        nedit.push_style_var(nedit.StyleVar.node_border_width, border_width)

        nedit.push_style_color(
            nedit.StyleColor.node_bg,
            ColorDB().find(
                'transparent'
            ).to_rgbaf()
        )
        nedit.push_style_color(
            nedit.StyleColor.node_border,
            ColorDB().find('transparent').to_rgbaf()
        )
        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 0.0))

        ##########################
        # render
        if self.node_id is None:
            self.node_id = nedit.NodeId.create()
            self.position_set = False
            nedit.set_node_position(
                self.node_id,
                (self.position_x, self.position_y)
            )
            nedit.set_node_z_position(self.node_id, self.position_z)

        self.render_sync_with_imgui()

        nedit.begin_node(self.node_id)

        # node content: nothing really, we are just going to draw on it
        imgui.begin_group()

        # draw the bar
        pmin, pmax = self.fill_interval()
        pmin = self.scale.fraction(pmin)
        pmax = self.scale.fraction(pmax)
        draw_list = imgui.get_window_draw_list()

        scale_bef = 0
        if self.show_scale and self.scale_position == self.LEFT:
            scale_bef = self.SCALE_SPACE

        if self.orientation == self.VERTICAL:
            if self.show_scale_set:
                self.width += self.SCALE_SPACE * (1 if self.show_scale else -1)
                self.show_scale_set = False

            bar_width = self.width - (self.SCALE_SPACE if self.show_scale else 0)

            c_tl = (
                scale_bef + self.position_x,
                self.position_y
            )
            c_br = (
                scale_bef + self.position_x + bar_width,
                self.position_y + self.height
            )

            p_tl = (
                scale_bef + self.position_x + border_width,
                self.position_y + (self.height - 2*border_width) * (1 - pmax) + border_width,
            )
            p_br = (
                scale_bef + self.position_x + (bar_width - border_width),
                self.position_y + (self.height - border_width) * (1 - pmin)
            )
        else:
            if self.show_scale_set:
                self.height += self.SCALE_SPACE * (1 if self.show_scale else -1)
                self.show_scale_set = False

            bar_height = self.height - (self.SCALE_SPACE if self.show_scale else 0)

            c_tl = (
                self.position_x,
                scale_bef + self.position_y
            )
            c_br = (
                self.position_x + self.width,
                scale_bef + self.position_y + bar_height
            )
            p_tl = (
                self.position_x + (self.width - border_width) * pmin + border_width,
                scale_bef + self.position_y + border_width
            )
            p_br = (
                self.position_x + (self.width - border_width) * pmax,
                scale_bef + self.position_y + (bar_height - border_width)
            )

        self.hot_x_min = self.position_x
        self.hot_x_max = self.position_x + self.width
        self.hot_y_min = self.position_y
        self.hot_y_max = self.position_y + self.height

        imgui.dummy([self.width, 1])
        imgui.dummy([1, self.height-1])

        color = self.get_color('stroke-color')
        draw_list.add_rect_filled(
            p_tl, p_br,
            ColorDB().backend.im_col32(color),
            border_round
        )
        draw_list.add_rect(
            c_tl, c_br,
            ColorDB().backend.im_col32(color),
            border_round
        )

        # draw the scale if required
        if self.show_scale:
            font_size = self.get_style('scale-font-size')

            if self.scale_ticks is None:
                if self.orientation == self.VERTICAL:
                    num_ticks = self.height / self.TICK_SPACE
                else:
                    num_ticks = self.width / self.TICK_SPACE

                self.scale_ticks = self.scale.ticks(num_ticks)

            for tick in self.scale_ticks:
                if self.orientation == self.VERTICAL:
                    tick_y = (
                        c_br[1] - border_width
                        - (c_br[1] - c_tl[1] - border_width) * self.scale.fraction(tick)
                    )
                    text_y = (
                        c_br[1]
                        - (0.75 * font_size)
                        - border_width
                        - (c_br[1] - c_tl[1] - font_size) * self.scale.fraction(tick)
                    )
                    if self.scale_position == self.LEFT:
                        tick_x = c_tl[0]
                    else:
                        tick_x = c_br[0] + self.TICK_LEN

                    draw_list.add_line(
                        (tick_x - self.TICK_LEN, tick_y),
                        (tick_x, tick_y),
                        ColorDB().backend.im_col32(color),
                        1.5
                    )
                    draw_list.add_text(
                        imgui.get_font(),
                        font_size,
                        [
                            tick_x - self.TICK_LEN - 2.5*font_size,
                            text_y
                        ],
                        ColorDB().backend.im_col32(color),
                        self.scale_format(tick)
                    )

                else:
                    tick_x = c_tl[0] + (c_br[0] - c_tl[0] - border_width) * self.scale.fraction(tick)
                    text_x = (
                        c_tl[0]
                        - 0.75 * font_size
                        + (c_br[0] - c_tl[0] - font_size) * self.scale.fraction(tick)
                    )
                    if self.scale_position == self.LEFT:
                        tick_y = c_tl[1]
                    else:
                        tick_y = c_br[1] + self.TICK_LEN

                    draw_list.add_line(
                        (tick_x, tick_y - self.TICK_LEN),
                        (tick_x, tick_y),
                        ColorDB().backend.im_col32(color),
                        1.5
                    )

                    with rotated(theta=-90, origin_x=1, origin_y=0):
                        draw_list.add_text(
                            imgui.get_font(),
                            font_size,
                            [
                                text_x,
                                tick_y - self.TICK_LEN - font_size,
                            ],
                            ColorDB().backend.im_col32(color),
                            self.scale_format(tick)
                        )

        imgui.end_group()

        # connections
        self.render_ports()

        # status badge
        self.render_badge()

        nedit.end_node()

        # update size and position after render
        p_tl = imgui.get_item_rect_min()
        p_br = imgui.get_item_rect_max()

        self.width = p_br[0] - p_tl[0]
        self.height = p_br[1] - p_tl[1]
        self.position_x, self.position_y = (p_tl[0], p_tl[1])

        # render
        ##########################

        imgui.pop_style_var()
        nedit.pop_style_color(2)  # color
        nedit.pop_style_var(3)  # padding, rounding

    def draw_ports(self):
        super().draw_ports()

    @mutates('position_x', 'position_y')
    async def move(self, x, y, **kwargs):
        await super().move(x, y, **kwargs)

    async def delete(self, **kwargs):
        await super().delete(**kwargs)

    def point_in_slider(self, x, y):
        is_in_slider = (
            self.hot_x_min <= x <= self.hot_x_max
            and self.hot_y_min <= y <= self.hot_y_max
        )
        return is_in_slider

    async def label_changed_cb(self, *args):
        pass

    async def set_size(self, width, height, **kwargs):
        await super().set_size(width, height, **kwargs)


class ImguiFaderElementImpl(
    FaderElementImpl, ImguiSlideMeterElementImpl, FaderElement
):
    backend_name = "imgui"


class ImguiBarMeterElementImpl(
    BarMeterElementImpl, ImguiSlideMeterElementImpl, BarMeterElement
):
    backend_name = "imgui"


class ImguiDialElementImpl(DialElementImpl, ImguiSlideMeterElementImpl, DialElement):

    def __init__(self, window, x, y):
        super().__init__(window, x, y)
        self.min_width = 15
        self.min_height = 15
        self.width = self.DEFAULT_W
        self.height = self.DEFAULT_H

    @mutates('position_x', 'position_y', 'width', 'height')
    def render(self):
        """
        dial element ("rotating" fader and meter)

        outline is a polyline, filling is a thick polyline
        """
        border_width = 1.25

        # style
        padding = self.get_style('padding')
        padding_tpl = (
            padding.get('left', 0),
            padding.get('top', 0),
            padding.get('right', 0),
            padding.get('bottom', 0)
        )
        nedit.push_style_var(nedit.StyleVar.node_rounding, 0)
        nedit.push_style_var(nedit.StyleVar.node_padding, ImVec4(*padding_tpl))
        nedit.push_style_var(nedit.StyleVar.node_border_width, border_width)

        nedit.push_style_color(
            nedit.StyleColor.node_bg,
            ColorDB().find(
                'transparent'
            ).to_rgbaf()
        )
        nedit.push_style_color(
            nedit.StyleColor.node_border,
            ColorDB().find('transparent').to_rgbaf()
        )
        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 0.0))

        ##########################
        # render
        if self.node_id is None:
            self.node_id = nedit.NodeId.create()
            self.position_set = False
            nedit.set_node_position(
                self.node_id,
                (self.position_x, self.position_y)
            )
            nedit.set_node_z_position(self.node_id, self.position_z)

        self.render_sync_with_imgui()

        nedit.begin_node(self.node_id)

        # node content: nothing really, we are just going to draw on it
        imgui.begin_group()

        if self.show_scale_set:
            self.height += self.scale_font_size * (1 if self.show_scale else -1)
            self.width += self.scale_font_size * (2 if self.show_scale else -2)
            self.show_scale_set = False

        # draw the bar
        pmin, pmax = self.fill_interval()
        pmin = self.scale.fraction(pmin)
        pmax = self.scale.fraction(pmax)
        draw_list = imgui.get_window_draw_list()

        self.hot_x_min = self.position_x
        self.hot_x_max = self.position_x + self.width
        self.hot_y_min = self.position_y
        self.hot_y_max = self.position_y + self.height

        imgui.dummy([self.width, 1])
        imgui.dummy([1, self.height-1])

        color = self.get_color('stroke-color')
        outer_radius = self.dial_radius
        inner_radius = self.dial_radius / 4
        theta_range = 2 * math.pi - (self.THETA_MIN - self.THETA_MAX)

        draw_list.path_arc_to(
            [self.position_x + self.width / 2,
             self.position_y + self.height / 2],
            outer_radius,
            self.THETA_MIN,
            2*math.pi + self.THETA_MAX,
            35
        )
        draw_list.path_line_to(
            [
                self.position_x + self.width / 2 + inner_radius*math.cos(self.THETA_MAX),
                self.position_y + self.height / 2 + inner_radius*math.sin(self.THETA_MAX)
            ]
        )
        draw_list.path_arc_to(
            [self.position_x + self.width / 2,
             self.position_y + self.height / 2],
            inner_radius,
            self.THETA_MAX,
            self.THETA_MIN - 2*math.pi,
            35
        )
        draw_list.path_stroke(
            ColorDB().backend.im_col32(color),
            imgui.ImDrawFlags_.closed,
            1.0
        )

        # the tasty filling
        draw_list.path_arc_to(
            [self.position_x + self.width / 2,
             self.position_y + self.height / 2],
            (outer_radius + inner_radius) / 2,
            self.THETA_MIN + pmin * theta_range,
            self.THETA_MIN + pmax * theta_range,
            35
        )

        draw_list.path_stroke(
            ColorDB().backend.im_col32(color),
            0,
            (outer_radius - inner_radius) * 0.95
        )

        # draw the scale if required
        if self.show_scale:
            font_size = self.get_style('scale-font-size')
            if self.scale_ticks is None:
                num_ticks = int(self.dial_radius / 10)
                if not num_ticks % 2:
                    num_ticks += 1
                self.scale_ticks = self.scale.ticks(num_ticks)

            for tick in self.scale_ticks:
                tick_theta = self.val2theta(tick)
                tick_x0, tick_y0 = self.p2r(self.dial_radius, tick_theta)
                tick_x1, tick_y1 = self.p2r(self.dial_radius + self.TICK_LEN, tick_theta)
                draw_list.add_line(
                    (tick_x0 + self.position_x, tick_y0 + self.position_y),
                    (tick_x1 + self.position_x, tick_y1 + self.position_y),
                    ColorDB().backend.im_col32(color),
                    1.0
                )

                txt_x, txt_y = self.p2r(
                    self.dial_radius + self.TICK_LEN + 0.5*self.scale_font_size,
                    tick_theta)

                label = self.scale_format(tick).strip()
                txt_x += 0.25 * self.scale_font_size * len(label) * (math.cos(tick_theta) - 1)
                txt_y -= 0.5*self.scale_font_size
                draw_list.add_text(
                    imgui.get_font(),
                    font_size,
                    (txt_x + self.position_x, txt_y + self.position_y),
                    ColorDB().backend.im_col32(color),
                    label
                )

        imgui.end_group()

        # connections
        self.render_ports()

        # status badge
        self.render_badge()

        nedit.end_node()

        # update size and position after render
        p_tl = imgui.get_item_rect_min()
        p_br = imgui.get_item_rect_max()

        self.width = p_br[0] - p_tl[0]
        self.height = p_br[1] - p_tl[1]
        self.position_x, self.position_y = (p_tl[0], p_tl[1])

        # render
        ##########################

        imgui.pop_style_var()
        nedit.pop_style_color(2)  # color
        nedit.pop_style_var(3)  # padding, rounding
