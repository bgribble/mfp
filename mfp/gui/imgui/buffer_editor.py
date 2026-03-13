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
        self.implot_limits_need_set = [None]
        self.implot_playhead = 0
        self.implot_playhead_needs_set = False

        self.shm_obj = None
        self.buffer_info = None
        self.buffer_data = None
        self.buffer_peaks = {}
        self.last_buffer = None

        self.channel_selections = [None]         # per-channel select box state (transient)
        self.channel_selections_active = [False]  # per-channel select box activity

    def focus(self):
        self.needs_focus = True

    def close(self):
        pass

    def set_playhead_at_pointer(self):
        self.implot_playhead_needs_set = True

    def buffer_grab(self):
        def offset(channel):
            return channel * self.buffer_info.size * self.FLOAT_SIZE
        if self.buffer_info is None:
            return None
        if self.shm_obj is None:
            self.shm_obj = SharedMemory(self.buffer_info.buf_id)

        self.last_buffer = datetime.now()
        self.buffer_data = []
        self.channel_selections = [None] * (self.buffer_info.channels + 1)
        self.channel_selections_active = [False] * (self.buffer_info.channels + 1)
        self.implot_limits = None
        self.implot_limits_need_set = [None] * (self.buffer_info.channels + 1)

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
        total_time = len(padded[0]) / self.buffer_info.rate
        sample_time = 1/self.buffer_info.rate

        self.implot_limits = implot.Rect(
            x_min=0, x_max=total_time, y_min=-1, y_max=1
        )
        self.implot_limits_need_set = [True] * (self.buffer_info.channels + 1)
        self.buffer_peaks["1"] = (
            padded,
            np.arange(0, total_time, sample_time, dtype=np.float32)
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

            x_values = np.arange(
                0, sample_time * peak_factor * len(padded) / 2,
                peak_factor * sample_time / 2, dtype=np.float32
            )
            self.buffer_peaks[str(peak_factor)] = (
                next_peaks, x_values
            )
            last_peaks = next_peaks

    def get_peak_scale(self):
        """
        called within a begin_plot()
        """
        limits = implot.get_plot_limits()
        compress = self.buffer_info.rate * (
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
    # toolbar
    def render_toolbar(self):
        from mfp.gui import image_utils
        line_height = imgui.get_text_line_height()
        imgui.set_next_window_size((self.app_window.canvas_panel_width, 4*line_height))
        imgui.set_next_window_pos((0, self.app_window.menu_height))

        imgui.begin(
            "bufedit_toolbar",
            flags=(
                imgui.WindowFlags_.no_collapse
                | imgui.WindowFlags_.no_move
                | imgui.WindowFlags_.no_title_bar
                | imgui.WindowFlags_.no_decoration
            ),
        )
        if imgui.is_window_hovered(imgui.FocusedFlags_.child_windows):
            imgui.set_window_focus()

        imgui.push_style_var(
            imgui.StyleVar_.frame_padding, (0.5 * line_height, 0.5 * line_height)
        )
        imgui.push_style_var(
            imgui.StyleVar_.item_spacing, (0.5 * line_height, 0.5 * line_height)
        )
        imgui.set_cursor_pos((0.5 * line_height, 0.5 * line_height))

        pause_tex = image_utils.load_texture_from_file("icons/media-playback-pause.png")
        pause_clicked = imgui.image_button(
            "##pause_btn", imgui.ImTextureRef(pause_tex[0]), [2*line_height, 2*line_height]
        )
        imgui.same_line()

        play_tex = image_utils.load_texture_from_file("icons/media-playback-start.png")
        play_clicked = imgui.image_button(
            "##play_btn", imgui.ImTextureRef(play_tex[0]), [2*line_height, 2*line_height]
        )
        imgui.same_line()

        stop_tex = image_utils.load_texture_from_file("icons/media-playback-stop.png")
        stop_clicked = imgui.image_button(
            "##stop_btn", imgui.ImTextureRef(stop_tex[0]), [2*line_height, 2*line_height]
        )
        imgui.same_line()

        home_tex = image_utils.load_texture_from_file("icons/media-skip-backward.png")
        home_clicked = imgui.image_button(
            "##home_btn", imgui.ImTextureRef(home_tex[0]), [2*line_height, 2*line_height]
        )
        imgui.same_line()

        end_tex = image_utils.load_texture_from_file("icons/media-skip-forward.png")
        end_clicked = imgui.image_button(
            "##end_btn", imgui.ImTextureRef(end_tex[0]), [2*line_height, 2*line_height]
        )
        imgui.same_line()

        record_tex = image_utils.load_texture_from_file("icons/media-record.png")
        record_clicked = imgui.image_button(
            "##record_btn", imgui.ImTextureRef(record_tex[0]), [2*line_height, 2*line_height]
        )
        imgui.same_line()

        loop_tex = image_utils.load_texture_from_file("icons/view-refresh.png")
        loop_clicked = imgui.image_button(
            "##loop_btn", imgui.ImTextureRef(loop_tex[0]), [2*line_height, 2*line_height]
        )
        imgui.same_line()

        imgui.pop_style_var(2)
        imgui.end()


    ########################################
    # plots
    def render_channels(self):
        implot.set_current_context(self.implot_context)

        num_channels = len(self.buffer_data or [])
        peak_scale = None
        peaks = None

        line_height = imgui.get_text_line_height()
        imgui.set_next_window_size([
            self.app_window.canvas_panel_width,
            self.app_window.canvas_panel_height - 4*line_height
        ])
        imgui.set_next_window_pos((0, 4*line_height + self.app_window.menu_height))
        imgui.begin(
            "##channelsview",
            flags=(
                imgui.WindowFlags_.no_collapse
                | imgui.WindowFlags_.no_title_bar
                | imgui.WindowFlags_.no_resize
                | imgui.WindowFlags_.no_saved_settings
                | imgui.WindowFlags_.no_move
            )
        )
        if implot.begin_aligned_plots("##aligned_plot_group"):
            implot.push_style_var(implot.StyleVar_.plot_padding, (2, 0))

            for channel in range(num_channels + 1):
                imgui.push_id(str(channel))
                if channel == 0:
                    height = line_height * 4
                    plot_flags = implot.Flags_.no_mouse_text
                    x_axis_flags = implot.AxisFlags_.no_label
                    y_axis_flags = implot.AxisFlags_.no_tick_labels | implot.AxisFlags_.no_label
                else:
                    height = line_height * 10
                    plot_flags = implot.Flags_.crosshairs | implot.Flags_.no_legend
                    x_axis_flags = implot.AxisFlags_.no_tick_labels | implot.AxisFlags_.no_label
                    y_axis_flags = implot.AxisFlags_.no_label

                if implot.begin_plot(
                    "##buf_edit_plot",
                    [-1, height],
                    flags=plot_flags
                ):
                    implot.setup_axes(
                        '', '',
                        x_flags=x_axis_flags, y_flags=y_axis_flags
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
                    if self.implot_playhead_needs_set:
                        pointer = implot.get_plot_mouse_pos()
                        if -1 <= pointer[1] <= 1:
                            self.implot_playhead = pointer[0]

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
                        self.implot_limits_need_set = [True] * (num_channels + 1)
                        self.implot_limits_need_set[channel] = False

                    if channel > 0:
                        # use the right subsampled data
                        if peak_scale is None:
                            peak_scale = self.get_peak_scale()
                            peaks = self.buffer_peaks[peak_scale]
                        y_values = peaks[0][channel - 1]
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

                    # playhead
                    implot.drag_line_x(0, self.implot_playhead, [1, 1, 1, 1])

                    if chan_sel.x.min != 0 and chan_sel.x.min != chan_sel.x.max:
                        self.implot_selection = chan_sel
                        self.channel_selections[channel] = chan_sel
                        self.channel_selections_active[channel] = True
                    implot.end_plot()
                imgui.pop_id()
            if self.implot_playhead_needs_set:
                self.implot_playhead_needs_set = False

            implot.pop_style_var()
            implot.end_aligned_plots()
        imgui.end()

    ########################################
    # render wrapper
    def render(self):
        keep_going = True
        line_height = imgui.get_text_line_height()

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

        self.render_toolbar()
        self.render_channels()

        imgui.end()

        imgui.pop_style_var(3)

        return keep_going
