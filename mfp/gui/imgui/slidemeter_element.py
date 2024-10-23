"""
imgui/slidemeter_element.py -- imgui backend for fader and dial elements
"""
from mfp import log
from flopsy import mutates
from imgui_bundle import imgui, imgui_node_editor as nedit

from ..slidemeter_element import (
    FaderElement,
    FaderElementImpl,
    BarMeterElement,
    BarMeterElementImpl,
    # DialElement,
    # DialElementImpl,
    SlideMeterElement,
)
from .base_element import ImguiBaseElementImpl


class ImguiSlideMeterElementImpl(ImguiBaseElementImpl):
    backend_name = "imgui"

    def __init__(self, window, x, y):
        super().__init__(window, x, y)
        self.node_id = None
        self.min_width = 10
        self.min_height = 10
        self.width = 22
        self.height = 100
        self.position_set = False

    def redraw(self):
        pass

    @mutates('position_x', 'position_y', 'width', 'height')
    def render(self):
        """
        slidemeter element (linear fader and meter)

        rectangular box, slight rounding, no label, draw_list to fill in the
        right portion of the scale
        """
        border_width = 1.25
        border_round = 3

        # style
        padding = self.get_style('padding')
        padding_tpl = (
            padding.get('left', 0),
            padding.get('top', 0),
            padding.get('right', 0),
            padding.get('bottom', 0)
        )
        nedit.push_style_var(nedit.StyleVar.node_rounding, border_round)
        nedit.push_style_var(nedit.StyleVar.node_padding, padding_tpl)
        nedit.push_style_var(nedit.StyleVar.node_border_width, border_width)

        nedit.push_style_color(
            nedit.StyleColor.node_bg,
            self.get_color(
                'fill-color:selected' if self.selected else 'fill-color'
            ).to_rgbaf()
        )
        nedit.push_style_color(
            nedit.StyleColor.node_border,
            self.get_color(
                'stroke-color:selected' if self.selected else 'stroke-color'
            ).to_rgbaf()
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
        imgui.dummy([self.width, 1])
        imgui.dummy([1, self.height-1])

        pmin, pmax = self.fill_interval()
        draw_list = imgui.get_window_draw_list()

        if self.orientation == self.VERTICAL:
            p_tl = (
                self.position_x + border_width,
                self.position_y + (self.height - 2*border_width) * (1 - pmax) + border_width,
            )
            p_br = (
                self.position_x + (self.width - border_width),
                self.position_y + (self.height - border_width) * (1 - pmin)
            )
        else:
            p_tl = (
                self.position_x + (self.width - border_width) * pmin + border_width,
                self.position_y + border_width
            )
            p_br = (
                self.position_x + (self.width - border_width) * pmax,
                self.position_y + (self.height - border_width)
            )

        self.hot_x_min = self.position_x
        self.hot_x_max = self.position_x + self.width
        self.hot_y_min = self.position_y
        self.hot_y_max = self.position_y + self.height

        draw_list.add_rect_filled(
            p_tl, p_br,
            imgui.IM_COL32(155, 155, 155, 255),
            border_round
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
        log.debug(f"[point_in_slider] canvas=({x}, {y}) in={is_in_slider}")
        log.debug(f"[point_in_slider] x={self.hot_x_min} {self.hot_x_max} y={self.hot_y_min} {self.hot_y_max}")

        return is_in_slider


    def redraw(self):
        pass

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
