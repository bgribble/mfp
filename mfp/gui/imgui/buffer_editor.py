"""
buffer_editor.py -- BufferEditor() class definition
"""
import os
from datetime import datetime
from posix_ipc import SharedMemory
from imgui_bundle import implot, imgui
from mfp import log
import numpy as np


class BufferEditor:
    FLOAT_SIZE = 4

    def __init__(self, app_window):
        self.app_window = app_window
        self.needs_focus = False
        self.implot_context = implot.create_context()
        self.implot_selection = None         # global selection range
        self.implot_limits = None            # global plot limits
        self.implot_limits_need_set = None

        self.shm_obj = None
        self.buffer_info = None
        self.buffer_data = None
        self.buffer_peaks = {}
        self.last_buffer = None

        self.channel_selections = []         # per-channel select box state (transient)
        self.channel_selections_active = []  # per-channel select box activity

    def focus(self):
        self.needs_focus = True

    def close(self):
        pass

    def buffer_grab(self):
        def offset(channel):
            return channel * self.buffer_info.size * self.FLOAT_SIZE
        if self.buffer_info is None:
            return None
        if self.shm_obj is None:
            self.shm_obj = SharedMemory(self.buffer_info.buf_id)

        self.last_buffer = datetime.now()
        self.buffer_data = []
        self.channel_selections = [None] * self.buffer_info.channels
        self.channel_selections_active = [False] * self.buffer_info.channels
        self.implot_limits = None
        self.implot_limits_need_set = [None] * self.buffer_info.channels

        try:
            for c in range(self.buffer_info.channels):
                os.lseek(self.shm_obj.fd, offset(c), os.SEEK_SET)
                slc = os.read(self.shm_obj.fd, int(self.buffer_info.size * self.FLOAT_SIZE))
                self.buffer_data.append(np.fromstring(slc, dtype=np.float32))
                # self.set_bounds(0, None, len(self.buffer_data[0])*1000/self.samplerate, None)
        except Exception as e:
            log.debug("[editor]: error grabbing data", e)
            import traceback
            traceback.print_exc()
            return None

        self.buffer_peaks = {}
        padding = 10 - len(self.buffer_data[0]) % 10
        padded = [
            np.pad(chan, (0, padding), mode='constant')
            for chan in self.buffer_data
        ]
        self.buffer_peaks["1"] = (
            padded,
            np.arange(len(padded[0]), dtype=np.float32)
        )
        last_peaks = padded

        for peak_factor in (10, 100, 1000, 10000):
            if peak_factor == 10:
                shape = 10
            else:
                shape = 20
            next_peaks = []
            for channel in last_peaks:
                maxima = channel.reshape(-1, shape).max(axis=1)
                minima = channel.reshape(-1, shape).min(axis=1)
                combined = np.ravel(np.column_stack((maxima, minima)))
                padding = 20 - len(combined) % 20
                padded = np.pad(combined, (0, padding), mode='constant')
                next_peaks.append(padded)

            x_values = np.arange(0, len(padded)*peak_factor / 2, peak_factor / 2, dtype=np.float32)
            self.buffer_peaks[str(peak_factor)] = (
                next_peaks, x_values
            )
            last_peaks = next_peaks

    def get_peak_scale(self):
        """
        called within a begin_plot()
        """
        limits = implot.get_plot_limits()
        compress = (
            (max(limits.x.max, 1.0) - limits.x.min)
            / self.app_window.canvas_panel_width
        )

        if compress < 10:
            peak_scale = "1"
        elif compress < 100:
            peak_scale = "10"
        elif compress < 1000:
            peak_scale = "100"
        elif compress < 10000:
            peak_scale = "1000"
        else:
            peak_scale = "10000"
        return peak_scale

    ########################################
    # renderer
    def render(self):
        keep_going = True

        imgui.set_next_window_size([
            self.app_window.canvas_panel_width,
            self.app_window.canvas_panel_height
        ])
        imgui.set_next_window_pos((0, self.app_window.menu_height))

        imgui.push_style_var(imgui.StyleVar_.window_border_size, 1)
        imgui.push_style_var(imgui.StyleVar_.window_padding, (2, 2))
        imgui.push_style_var(imgui.StyleVar_.frame_padding, (2, 2))

        imgui.begin(
            "Buffer editor",
            flags=(
                imgui.WindowFlags_.no_collapse
                | imgui.WindowFlags_.no_title_bar
                | imgui.WindowFlags_.no_resize
                | imgui.WindowFlags_.no_saved_settings
                | imgui.WindowFlags_.no_move
            )
        )

        if imgui.is_window_hovered(imgui.FocusedFlags_.child_windows):
            self.app_window.selected_window = "bufedit"

        if self.needs_focus:
            imgui.set_window_focus()
            imgui.set_window_collapsed(False)
            self.needs_focus = False

        ########################################
        # the plots
        implot.set_current_context(self.implot_context)

        num_channels = len(self.buffer_data or [])
        peak_scale = None
        peaks = None

        for channel in range(num_channels):
            imgui.push_id(str(channel))
            if implot.begin_plot(
                "##buf_edit_plot",
                flags=implot.Flags_.crosshairs | implot.Flags_.no_legend
            ):
                implot.setup_axes(
                    '', '',
                    x_flags=implot.AxisFlags_.no_tick_labels | implot.AxisFlags_.no_label,
                    y_flags=implot.AxisFlags_.no_label,
                )
                implot.setup_axis_limits(
                    implot.ImAxis_.y1.value, -1, 1, implot.Cond_.always.value
                )

                if not self.implot_limits:
                    self.implot_limits = implot.get_plot_limits()

                # this is to reset limits after the boxselect adjusts zoom
                if self.implot_limits_need_set[channel]:
                    implot.setup_axis_limits(
                        implot.ImAxis_.x1.value,
                        self.implot_limits.x.min,
                        self.implot_limits.x.max,
                        implot.Cond_.always.value
                    )
                    self.implot_limits_need_set[channel] = False

                chan_sel = implot.get_plot_selection()
                chan_limits = implot.get_plot_limits()
                if chan_sel.x.min == 0 and chan_sel.x.max == 0:
                    if self.channel_selections_active[channel]:
                        self.implot_limits_need_set[channel] = True
                        self.channel_selections_active[channel] = False
                if (
                    not self.implot_limits_need_set[channel]
                    and (
                        chan_limits.x.min != self.implot_limits.x.min
                        or chan_limits.x.max != self.implot_limits.x.max
                    )
                ):
                    self.implot_limits = chan_limits
                    self.implot_limits_need_set = [True] * num_channels
                    self.implot_limits_need_set[channel] = False

                # use the right subsampled data
                if peak_scale is None:
                    peak_scale = self.get_peak_scale()
                    peaks = self.buffer_peaks[peak_scale]
                y_values = peaks[0][channel]
                x_values = peaks[1]

                # the actual line!
                implot.plot_line("Buffer edit", x_values, y_values, flags=0)

                # if we have a selection, show it as a drag rect
                if not self.channel_selections_active[channel] and self.implot_selection:
                    ss = self.implot_selection
                    rect = implot.drag_rect(
                        0, ss.x.min, 1, ss.x.max, -1, [0, 1, 0, 1]
                    )
                    if rect[1] != ss.x.min or rect[3] != ss.x.max:
                        ss.x.min = rect[1]
                        ss.x.max = rect[3]
                        self.channel_selections[channel] = ss
                        self.implot_selection = ss

                if chan_sel.x.min != 0 and chan_sel.x.min != chan_sel.x.max:
                    self.implot_selection = chan_sel
                    self.channel_selections[channel] = chan_sel
                    self.channel_selections_active[channel] = True
                implot.end_plot()
            imgui.pop_id()
        imgui.end()
        imgui.pop_style_var(3)
        return keep_going
