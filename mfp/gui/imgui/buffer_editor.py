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
        self.implot_selection = None

        self.shm_obj = None
        self.buffer_info = None
        self.buffer_data = None
        self.buffer_peaks = {}
        self.last_buffer = None

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
        # the plot
        implot.set_current_context(self.implot_context)
        if implot.begin_plot(
            "##buf_edit_plot",
            flags=implot.Flags_.crosshairs | implot.Flags_.no_legend
        ):
            implot.setup_axes('x', 'y')
            implot.setup_axis_limits(
                implot.ImAxis_.y1.value, -1, 1, implot.Cond_.always.value
            )

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

            if self.buffer_peaks:
                peaks = self.buffer_peaks[peak_scale]
                y_values = peaks[0]
                x_values = peaks[1]
                for curve in y_values:
                    implot.plot_line(
                        "Sample plot",
                        x_values, curve,
                        flags=0
                    )

            sel = implot.get_plot_selection()
            if sel.x.min != 0 and sel.x.min != sel.x.max:
                self.implot_selection = sel
            elif self.implot_selection is not None:
                self.implot_selection = None
            implot.end_plot()
        imgui.end()
        imgui.pop_style_var(3)
        return keep_going
