"""
imgui/plot_element.py -- imgui backend for x/y plot elements, using implot

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from datetime import datetime
import asyncio
import os

from flopsy import mutates, saga
import numpy as np
from posix_ipc import SharedMemory

from imgui_bundle import imgui_node_editor as nedit, implot, imgui
from mfp.gui_main import MFPGUI
from mfp import log
from .base_element import ImguiBaseElementImpl
from ..plot_element import (
    PlotElement,
    PlotElementImpl
)


def find_data_bounds(data_array, point_accessor):
    min_x = min_y = max_x = max_y = None

    for data in data_array:
        for datapoint in data:
            point = point_accessor(datapoint)
            x = point[0]
            y = point[1]

            if x is not None:
                if min_x is None or x < min_x:
                    min_x = x
                if max_x is None or x > max_x:
                    max_x = x

            if y is not None:
                if min_y is None or y < min_y:
                    min_y = y
                if max_y is None or y > max_y:
                    max_y = y

    if min_x is not None:
        dx = (max_x - min_x) * 0.1
        dy = (max_y - min_y) * 0.1

        min_x = min_x - dx
        max_x = max_x + dx
        min_y = min_y - dy
        max_y = max_y + dy

    return (min_x, min_y, max_x, max_y)


class ImguiPlotElementImpl(PlotElementImpl, ImguiBaseElementImpl, PlotElement):
    backend_name = "imgui"
    FLOAT_SIZE = 4

    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        # create display
        width = self.INIT_WIDTH + self.WIDTH_PAD
        height = self.INIT_HEIGHT + self.LABEL_SPACE + self.HEIGHT_PAD

        self.width = width
        self.height = height
        self.plot_width = width
        self.plot_height = height
        self.min_width = width
        self.min_height = height

        self.samplerate = window.dsp_info.get("samplerate", 48000)

        self.scroll_timebase = None

        self.plot_type = "none"
        self.plot_style = {}

        self.implot_context = implot.create_context()

        self.message_data = {}
        self.buffer_data = []
        self.buf_info = None
        self.shm_obj = None

        self.last_buffer = None
        self.last_message = None
        self.last_bounds = None
        self.last_bounds_cache = None

    async def set_size(self, width, height, **kwargs):
        await super().set_size(width, height, **kwargs)

    @saga('x_min', 'x_max', 'y_min', 'y_max')
    async def on_bounds_update(self, action, state_diff, previous):
        self.send_params()

    # methods useful for interaction
    @mutates('x_min', 'x_max', 'y_min', 'y_max')
    def set_bounds(self, x_min, y_min, x_max, y_max):
        if x_min is not None and x_min != self.x_min:
            self.x_min = x_min
        if x_max is not None and x_max != self.x_max:
            self.x_max = x_max
        if y_min is not None and y_min != self.y_min:
            self.y_min = y_min
        if y_max is not None and y_max != self.y_max:
            self.y_max = y_max

    @mutates('position_x', 'position_y', 'width', 'height')
    def render(self):
        """
        plot element

        * implot wrapper with frame
        """

        # style
        padding = self.get_style('padding', {})
        padding_tpl = (
            padding.get('left', 0),
            padding.get('top', 0),
            padding.get('right', 0),
            padding.get('bottom', 0)
        )
        nedit.push_style_var(nedit.StyleVar.node_rounding, 0.25)
        nedit.push_style_var(nedit.StyleVar.node_padding, padding_tpl)
        nedit.push_style_var(nedit.StyleVar.node_border_width, 1.25)

        nedit.push_style_color(
            nedit.StyleColor.node_bg,
            self.get_color('fill-color').to_rgbaf()
        )
        nedit.push_style_color(
            nedit.StyleColor.node_border,
            self.get_color('stroke-color').to_rgbaf()
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

        # node content: label and implot plot
        imgui.begin_group()
        self.label.render()

        # the plot
        implot.set_current_context(self.implot_context)

        if implot.begin_plot(f"##{self.obj_id}__plot", [self.plot_width, self.plot_height]):
            implot.setup_axes(
                self.x_label or '', self.y_label or '', 0, 0
            )

            x_min, y_min, x_max, y_max = self.find_axis_bounds()

            if x_min is not None and x_max is not None:
                implot.setup_axis_limits(
                    implot.ImAxis_.x1.value, x_min, x_max, implot.Cond_.always.value
                )
            if y_min is not None and y_max is not None:
                implot.setup_axis_limits(
                    implot.ImAxis_.y1.value, y_min, y_max, implot.Cond_.always.value
                )

            if self.plot_type == "scatter":
                self.render_scatter(x_min, y_min, x_max, y_max)

            if self.plot_type == "scope":
                self.render_scope(x_min, y_min, x_max, y_max)

            implot.end_plot()

        # pad out to min size
        content_w, content_h = imgui.get_item_rect_size()
        if content_w < self.min_width:
            imgui.same_line()
            imgui.dummy([self.min_width - content_w, 1])

        if content_h < self.min_height:
            imgui.dummy([1, self.min_height - content_h])
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

        """
        signal the main app when the draw is complete (to unlock the
        shared mem area for writing)
        """
        async def notify_later(sleep_ms):
            await asyncio.sleep(sleep_ms / 1000.0)
            await MFPGUI().mfp.send_methodcall(self.obj_id, 0, "draw_complete")

        def notify_complete():
            MFPGUI().async_task(
                MFPGUI().mfp.send_methodcall(self.obj_id, 0, "draw_complete")
            )

        if self.last_buffer and (not self.last_draw or self.last_buffer > self.last_draw):
            if self.last_draw is not None:
                time_since_last = datetime.now() - self.last_draw
                delta_msec = time_since_last.total_seconds() * 1000.0
                self.last_draw = datetime.now()
                if delta_msec > self.min_interval:
                    notify_complete()
                else:
                    MFPGUI().async_task(notify_later(self.min_interval-delta_msec))
            else:
                self.last_draw = datetime.now()
                notify_complete()

    def find_axis_bounds(self):
        data_x_min = data_x_max = data_y_min = data_y_max = None

        if self.plot_type == "scatter":
            if self.last_message and self.last_bounds and self.last_bounds > self.last_message:
                return self.last_bounds_cache

            data_x_min, data_y_min, data_x_max, data_y_max = find_data_bounds(
                self.message_data.values(), lambda pt: pt[1]
            )
        if self.plot_type == "scope":
            if self.last_bounds and self.last_buffer and self.last_bounds > self.last_buffer:
                return self.last_bounds_cache

            data_x_min, data_y_min, data_x_max, data_y_max = find_data_bounds(
                self.buffer_data, lambda pt: [None, pt]
            )

        x_min = self.x_min
        x_max = self.x_max
        y_min = self.y_min
        y_max = self.y_max

        if any(x is None for x in [self.x_min, self.x_max, self.y_min, self.y_max]):
            x_min = self.x_min if self.x_min is not None else data_x_min
            x_max = self.x_max if self.x_max is not None else data_x_max
            y_min = self.y_min if self.y_min is not None else data_y_min
            y_max = self.y_max if self.y_max is not None else data_y_max

            if x_min is not None and x_min == x_max:
                x_min = x_min - 0.5
                x_max = x_min + 1
            if y_min is not None and y_min == y_max:
                y_min = y_min - 0.5
                y_max = y_min + 1

        self.last_bounds_cache = (x_min, y_min, x_max, y_max)
        self.last_bounds = datetime.now()

        return self.last_bounds_cache

    def render_scope(self, x_min, y_min, x_max, y_max):
        for curve, curve_data in enumerate(self.buffer_data):
            title = self.curve_label.get(curve, f"Curve {curve}")
            implot.plot_line(
                title,
                curve_data,
                xscale=1000/self.samplerate,
                xstart=0,
                flags=0
            )

    def render_scatter(self, x_min, y_min, x_max, y_max):
        for curve, points in self.message_data.items():
            time_adjusted = [
                p[1]
                if self.scroll_timebase is None
                else [
                    (p[1][0] - (datetime.now() - self.scroll_timebase).total_seconds()),
                    p[1][1]
                ]
                for p in points
            ]

            x_data = [
                p[0] for p in time_adjusted
                if ((x_min is None or p[0] >= x_min) and (x_max is None or p[0] <= x_max))
            ]
            y_data = [
                p[1] for p in time_adjusted
                if ((x_min is None or p[0] >= x_min) and (x_max is None or p[0] <= x_max))
            ]
            title = self.curve_label.get(curve, f"Curve {curve}")
            implot.plot_scatter(
                title, np.array(x_data), np.array(y_data)
            )

    def draw_ports(self):
        super().draw_ports()

    # append scatter data
    def append(self, point, curve=0):
        curve = int(curve)
        pts = self.message_data.setdefault(curve, [])
        ptnum = len(pts)
        pts.append([ptnum, point])

    # grab scope data from buffer
    def buffer_grab(self):
        def offset(channel):
            return channel * self.buf_info.size * self.FLOAT_SIZE

        if self.buf_info is None:
            return None
        if self.shm_obj is None:
            self.shm_obj = SharedMemory(self.buf_info.buf_id)

        self.last_buffer = datetime.now()
        self.buffer_data = []
        try:
            for c in range(self.buf_info.channels):
                os.lseek(self.shm_obj.fd, offset(c), os.SEEK_SET)
                slc = os.read(self.shm_obj.fd, int(self.buf_info.size * self.FLOAT_SIZE))
                self.buffer_data.append(np.fromstring(slc, dtype=np.float32))
                self.set_bounds(0, None, len(self.buffer_data[0])*1000/self.samplerate, None)
        except Exception as e:
            log.debug("[imgui/plot]: error grabbing data", e)
            import traceback
            traceback.print_exc()
            return None

    def command(self, action, data):
        # not sure where this is used
        # if self.xyplot.command(action, data):
        #     return True
        if action == "clear":
            self.buffer_data = []
            self.message_data = {}
            self.last_message = None
            self.last_buffer = None
            return True
        if action == "bounds":
            self.set_bounds(*data)
            return True
        if action == "add":
            for c in data:
                for p in data[c]:
                    self.append(p, c)
            self.last_message = datetime.now()
            return True
        if action == "buffer":
            self.buf_info = data
            self.shm_obj = None

            for c in range(data.channels):
                if c not in self.curve_label:
                    self.curve_label[c] = f"Curve {c}"
                if c not in self.mark_type:
                    self.mark_type[c] = "default"
                if c not in self.stroke_type:
                    self.stroke_type[c] = "default"
            return True
        if action == "grab":
            self.buffer_grab()
            return True
        if action == "roll":
            self.set_bounds(-6, None, 0, None)
            self.scroll_timebase = datetime.now()
            return True
        if action == "stop":
            self.scroll_timebase = None
            return True
        if super().command(action, data):
            return True

        return False
