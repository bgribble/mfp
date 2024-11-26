"""
imgui/plot_element.py -- imgui backend for x/y plot elements, using implot

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from datetime import datetime
import asyncio
import os

from flopsy import mutates
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

        self.plot_type = "none"
        self.plot_style = {}

        self.implot_context = implot.create_context()

        self.scatter_data = {}
        self.buffer_data = []
        self.buf_info = None
        self.shm_obj = None

        self.last_buffer = None

        self.y_min = -1
        self.y_max = 1

    async def set_size(self, width, height, **kwargs):
        await super().set_size(width, height, **kwargs)

    # methods useful for interaction
    @mutates('x_min', 'x_max', 'y_min', 'y_max')
    def set_bounds(self, x_min, y_min, x_max, y_max):
        update = False

        if x_min != self.x_min:
            self.x_min = x_min
            update = True
        if x_max != self.x_max:
            self.x_max = x_max
            update = True
        if y_min is not None and y_min != self.y_min:
            self.y_min = y_min
            update = True
        if y_max is not None and y_max != self.y_max:
            self.y_max = y_max
            update = True

        if update:
            self.send_params()

    @mutates('position_x', 'position_y', 'width', 'height')
    def render(self):
        """
        plot element

        * implot wrapper with frame
        """

        # style
        padding = self.get_style('padding')
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
        implot.set_next_axes_limits(
            self.x_min, self.x_max, self.y_min, self.y_max
        )
        if implot.begin_plot(f"##{self.obj_id}__plot", [self.plot_width, self.plot_height]):
            if self.plot_type == "scatter":
                for curve, points in self.scatter_data.items():
                    x_data = [p[1][0] for p in points]
                    y_data = [p[1][1] for p in points]
                    implot.plot_scatter(
                        f"Curve {curve}",
                        np.array(x_data), np.array(y_data)
                    )
            if self.plot_type == "scope":
                for curve_num, curve_data in enumerate(self.buffer_data):
                    implot.plot_line(
                        f"Curve {curve_num}",
                        curve_data,
                        xscale=1000/self.samplerate,
                        xstart=0,
                        flags=0
                    )

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

    def draw_ports(self):
        super().draw_ports()

    # append scatter data
    def append(self, point, curve=0):
        curve = int(curve)
        pts = self.scatter_data.setdefault(curve, [])
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
        #if self.xyplot.command(action, data):
        #    return True
        if action == "clear":
            return True
        if action == "bounds":
            return True
        if action == "add":
            for c in data:
                for p in data[c]:
                    self.append(p, c)
            return True
        if action == "buffer":
            self.buf_info = data
            self.shm_obj = None
            return True
        if action == "grab":
            self.buffer_grab()
            return True

        if super().command(action, data):
            return True

        return False
