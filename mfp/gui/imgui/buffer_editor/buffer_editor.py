"""
buffer_editor.py -- BufferEditor() class definition
"""
import asyncio
import os
import math
from datetime import datetime
from imgui_bundle import implot, imgui
import numpy as np

from mfp import log
from mfp.gui import image_utils
from mfp.gui.colordb import ColorDB
from posix_ipc import SharedMemory


class BufferEditor:
    """
    Visual editor for buffer~ contents as audio waveforms
    """
    SECONDS = "seconds"
    BEATS = "beats"

    FLOAT_SIZE = 4
    SIZE_IN_LINES = {
        'small': 4,
        'normal': 6,
        'large': 10,
        'x-large': 16,
    }

    def __init__(self, app_window):
        self.app_window = app_window
        self.needs_focus = False

        self.implot_context = implot.create_context()
        self.implot_selection = None         # global selection range
        self.implot_limits = None            # global plot limits
        self.implot_limits_need_set = [None]
        self.implot_limits_counter = 0
        self.implot_playhead = 0
        self.implot_playhead_needs_set = False
        self.implot_playhead_start_time = None
        self.implot_playhead_start_pos = None
        self.implot_playhead_looping = False
        self.implot_total_time = 0
        self.implot_plot_hovered = False

        self.all_buffers = []

        self.shm_obj = None                  # primary (original) buffer
        self.buffer_source_info = None
        self.buffer_info = None
        self.buffer_data = None
        self.buffer_data_last_update = None
        self.buffer_peaks = {}
        self.buffer_units = self.SECONDS
        self.buffer_bpm = 60

        self.working_patch_id = None
        self.working_patch_info = None
        self.working_buf_id = None
        self.working_buf_obj = None          # working buffer, shared btw source/sink
        self.working_buf_info = None
        self.working_source_id = None
        self.working_source_info = None
        self.working_sink_id = None
        self.working_sink_info = None
        self.working_trigger_id = None
        self.working_ampl_buf_id = None
        self.working_ampl_buf_obj = None
        self.working_ampl_buf_info = None
        self.working_mon_gain = {}

        self.fx_patch_id = None
        self.fx_patch_elements = {}
        self.fx_patch_channel_enable = []

        self.channel_selections = [None]          # per-channel select box state (transient)
        self.channel_selections_active = [False]  # per-channel select box activity
        self.channel_options = []                 # switch settings for channels
        self.rec_enabled = 0
        self.rec_recording = False
        self.rec_recording_updated = None

        self.spectral_data_cache = {}

        self.clipboard_data = None
        self.clipboard_size = None
        self.clipboard_pos = None

    def focus(self):
        self.needs_focus = True

    async def close(self):
        await self.close_working_patch()

    def set_playhead_at_pointer(self):
        self.implot_playhead_needs_set = True

    def set_buffer_bpm(self, bpm):
        if not bpm:
            return

        if self.buffer_units == self.BEATS:
            ratio = bpm / self.buffer_bpm
            if self.implot_selection:
                self.implot_selection.x.min *= ratio
                self.implot_selection.x.max *= ratio
            if self.implot_limits:
                self.implot_limits.x.min *= ratio
                self.implot_limits.x.max *= ratio
            if self.implot_playhead:
                self.implot_playhead *= ratio

        self.buffer_bpm = bpm

    def position_to_sample(self, position):
        if self.buffer_units == self.BEATS:
            return (60 * position / self.buffer_bpm) * self.buffer_info.rate
        else:
            return position * self.buffer_info.rate

    def sample_to_position(self, sample):
        if self.buffer_units == self.BEATS:
            return (sample / self.buffer_info.rate) * (self.buffer_bpm / 60)
        else:
            return sample / self.buffer_info.rate

    ########################################
    # plots
    def render_channels(self, toolbar_height):
        from mfp.gui_main import MFPGUI
        from . import menu_button
        implot.set_current_context(self.implot_context)
        plot_hovered = False

        plot_width = None
        plot_height = None
        num_channels = len(self.buffer_data or [])
        peak_scale = None
        peaks = None

        line_height = imgui.get_text_line_height()
        imgui.set_next_window_size([
            self.app_window.window_width,
            self.app_window.console_panel_height - self.app_window.menu_height - toolbar_height
        ])
        xpos, ypos = imgui.get_window_pos()
        imgui.set_next_window_pos((xpos, ypos + toolbar_height))

        source_info = self.working_source_info or self.buffer_source_info
        binfo = self.working_buf_info or self.buffer_info

        if not binfo:
            return

        fname = binfo.file_name or 'No file'
        dots = image_utils.load_texture_from_file("icons/dots-horiz.png")

        channel_ampls = [0] * (4 * self.buffer_info.channels)
        if self.working_ampl_buf_obj:
            os.lseek(self.working_ampl_buf_obj.fd, 0, os.SEEK_SET)
            slc = os.read(
                self.working_ampl_buf_obj.fd,
                int(self.working_ampl_buf_info.channels * self.FLOAT_SIZE)
            )
            for ind, ampl in enumerate(np.fromstring(slc, dtype=np.float32)):
                if ind >= len(channel_ampls):
                    continue
                channel_ampls[ind] = float(ampl)

        frames = binfo.size
        ttime = frames / self.buffer_info.rate
        display_name = f"{source_info.get('name')} ({fname}) channels={self.buffer_info.channels}"
        imgui.begin(
            f"{display_name} time={ttime:.1f}s frames={frames}##channelsview",
            flags=(
                imgui.WindowFlags_.no_collapse
                | imgui.WindowFlags_.no_resize
                | imgui.WindowFlags_.no_saved_settings
                | imgui.WindowFlags_.no_move
            )
        )
        if imgui.is_window_hovered(imgui.FocusedFlags_.child_windows):
            self.app_window.zone_hovered("bufedit")

        if implot.begin_aligned_plots("##aligned_plot_group"):
            implot.push_style_var(implot.StyleVar_.plot_padding, (2, 0))

            if self.implot_playhead_start_time and not self.implot_playhead_needs_set:
                playhead_offset = (
                    datetime.now() - self.implot_playhead_start_time
                ).total_seconds()
                if self.implot_playhead_looping and self.implot_selection:
                    raw_offset = self.implot_playhead_start_pos + playhead_offset
                    if raw_offset < self.implot_selection.x.min:
                        self.implot_playhead = self.implot_selection.x.min
                    elif raw_offset <= self.implot_selection.x.max:
                        self.implot_playhead = raw_offset
                    else:
                        window_size = self.implot_selection.x.max - self.implot_selection.x.min
                        window_offset = raw_offset - self.implot_selection.x.min
                        self.implot_playhead = (
                            self.implot_selection.x.min
                            + (window_offset % window_size)
                        )
                else:
                    self.implot_playhead = (
                        self.implot_playhead_start_pos + playhead_offset
                    )

                if self.implot_playhead > self.implot_total_time:
                    self.implot_playhead_start_time = None
                    self.implot_playhead_looping = False
                    log.debug(f"[play] Stopping at end of buffer, options={self.channel_options}")
                    MFPGUI().async_task(self.playhead_pause())

            options_changed = False
            limits_changed = False
            limit_delay_frames = 2

            for channel in range(num_channels + 1):
                channel_tool_width = 100

                imgui.push_id(str(channel))
                if channel == 0:
                    height = line_height * 4
                    plot_flags = implot.Flags_.no_mouse_text
                    x_axis_flags = implot.AxisFlags_.no_label
                    y_axis_flags = implot.AxisFlags_.no_tick_labels | implot.AxisFlags_.no_label
                else:
                    chan_size = self.channel_options[channel - 1].get("size", "normal")
                    chan_size_lines = self.SIZE_IN_LINES.get(chan_size, 6)
                    height = line_height * chan_size_lines
                    plot_flags = implot.Flags_.crosshairs | implot.Flags_.no_legend
                    x_axis_flags = implot.AxisFlags_.no_tick_labels | implot.AxisFlags_.no_label
                    y_axis_flags = implot.AxisFlags_.no_tick_labels | implot.AxisFlags_.no_label

                if channel == 0:
                    imgui.dummy([channel_tool_width, height])
                    imgui.same_line()
                else:
                    imgui.push_font(imgui.get_font(), 14)
                    imgui.begin_group()
                    imgui.dummy([1, height-1])
                    imgui.same_line()

                    # config buttons
                    imgui.begin_group()
                    imgui.push_style_color(
                        imgui.Col_.frame_bg, ColorDB().find("default-canvas-color").to_rgbaf()
                    )
                    imgui.push_style_var(imgui.StyleVar_.item_spacing, [0, 2])
                    for option in ("mute", "solo", "rec", "fx"):
                        changed, checked = imgui.checkbox(
                            option.upper(),
                            self.channel_options[channel - 1].get(option, False)
                        )
                        if changed:
                            self.channel_options[channel - 1][option] = checked
                            options_changed = True

                    imgui.pop_style_var()
                    imgui.pop_style_color()
                    imgui.end_group()
                    imgui.same_line()

                    # channel menu and meters
                    in_rms = in_peak = out_rms = out_peak = 0
                    achan = 4*(channel-1)

                    if len(channel_ampls) > achan + 3:
                        in_rms = channel_ampls[achan]
                        in_peak = channel_ampls[achan+1]
                        out_rms = channel_ampls[achan+2]
                        out_peak = channel_ampls[achan+3]

                    imgui.dummy([10, 1])
                    imgui.same_line()

                    imgui.begin_group()

                    # channel menu
                    imgui.dummy([1, 3])
                    imgui.push_style_var(imgui.StyleVar_.frame_padding, [4, 6])
                    imgui.push_style_var(imgui.StyleVar_.frame_rounding, 4)
                    if imgui.image_button(
                        "##channel_menubutton", imgui.ImTextureRef(dots[0]),
                        [15, 3]
                    ):
                        imgui.open_popup("##bufedit_channel_popup")

                    menu_button.render_channel_menu(self.app_window, channel-1)
                    th = imgui.get_item_rect_size()[1]
                    imgui.pop_style_var(2)
                    imgui.dummy([1, 3])

                    # meters
                    imgui.begin_group()
                    self.render_meter_bar(
                        min(height, 6 * line_height) - th - 10, in_rms, in_peak,
                    )
                    imgui.end_group()
                    imgui.same_line()
                    imgui.dummy([3, 1])
                    imgui.same_line()

                    imgui.begin_group()
                    self.render_meter_bar(
                        min(height, 6 * line_height) - th - 10, out_rms, out_peak
                    )
                    imgui.end_group()
                    imgui.end_group()
                    imgui.end_group()
                    spacer = channel_tool_width - imgui.get_item_rect_size()[0]
                    imgui.same_line()
                    imgui.dummy([spacer, 1])
                    imgui.same_line()
                    imgui.pop_font()

                # the plot itself
                imgui.begin_group()

                if implot.begin_plot("##buf_edit_plot", [-1, height], flags=plot_flags):
                    implot.setup_axes(
                        '', '',
                        x_flags=x_axis_flags, y_flags=y_axis_flags
                    )
                    implot.setup_axis_limits(
                        implot.ImAxis_.y1.value, -1, 1, implot.Cond_.always.value
                    )
                    if self.buffer_units == self.BEATS:
                        x_scale = self.buffer_bpm / 60
                    else:
                        x_scale = 1

                    # set up plot limits if not already set
                    if channel == 0:
                        if not self.implot_limits:
                            self.implot_limits = implot.Rect(
                                x_min=0, x_max=1, y_min=-1, y_max=1
                            )
                            self.implot_limits_need_set = [True] * (num_channels + 1)
                        elif self.implot_limits_counter > 0:
                            self.implot_limits_counter -= 1

                    # this is to reset limits after new file or change in view
                    if self.implot_limits_need_set[channel] or self.implot_limits_counter > 0:
                        implot.setup_axis_limits(
                            implot.ImAxis_.x1.value,
                            self.implot_limits.x.min,
                            self.implot_limits.x.max,
                            implot.Cond_.always.value
                        )
                        self.implot_limits_need_set[channel] = False

                    # catch changes done by implot when scroll-zooming
                    chan_sel = implot.get_plot_selection()
                    chan_limits = implot.get_plot_limits()

                    if chan_sel.x.min not in (0, chan_sel.x.max):
                        self.implot_selection = chan_sel
                        self.channel_selections[channel] = chan_sel
                        self.channel_selections_active[channel] = True
                        MFPGUI().async_task(
                            self.playhead_update_selection()
                        )

                    if (
                        not self.implot_limits_need_set[channel]
                        and (
                            chan_limits.x.min != self.implot_limits.x.min
                            or chan_limits.x.max != self.implot_limits.x.max
                        )
                    ):
                        if (
                            self.implot_limits_counter <= 0
                            and not limits_changed
                        ):
                            limits_changed = chan_limits

                    if self.implot_playhead_needs_set:
                        pointer = implot.get_plot_mouse_pos()
                        if -1 <= pointer[1] <= 1:
                            MFPGUI().async_task(self.playhead_move(pointer[0]))

                    if chan_sel.x.min == 0 and chan_sel.x.max == 0:
                        if self.channel_selections_active[channel]:
                            self.implot_limits_need_set[channel] = True
                            limits_changed = self.implot_limits
                            limit_delay_frames = 1
                            self.channel_selections_active[channel] = False

                    if channel > 0:
                        # use the right subsampled data
                        if peak_scale is None:
                            peak_scale = self.get_peak_scale(self.implot_limits)
                            peaks = self.buffer_peaks[peak_scale]
                        y_values = peaks[0][channel - 1]

                        x_values = peaks[1] * x_scale

                        # the actual line!
                        implot.plot_line("Buffer edit", x_values, y_values)

                    # if we have a selection, show it as a drag rect
                    drag_color = [*self.app_window.get_color("selbox-fill-color").to_rgbaf()]
                    drag_color[3] = 1

                    if not self.channel_selections_active[channel] and self.implot_selection:
                        ss = self.implot_selection
                        rect = implot.drag_rect(0, ss.x.min, 1, ss.x.max, -1, drag_color)

                        if rect[1] != ss.x.min or rect[3] != ss.x.max:
                            ss.x.min = rect[1]
                            ss.x.max = rect[3]
                            self.channel_selections[channel] = ss
                            self.implot_selection = ss
                            MFPGUI().async_task(self.playhead_update_selection())

                    # playhead
                    implot.drag_line_x(0, self.implot_playhead, drag_color)

                    implot.end_plot()
                    plot_width, plot_height = imgui.get_item_rect_size()

                    if imgui.is_item_hovered():
                        plot_hovered = True

                show_spectrogram = channel > 0 and self.channel_options[channel-1].get("spectrogram")
                if show_spectrogram and implot.begin_plot(
                    "##buf_edit_spectrogram",
                    [-1, height],
                    flags=implot.Flags_.no_legend | implot.Flags_.no_mouse_text
                ):
                    x_axis_flags = (
                        implot.AxisFlags_.no_tick_labels | implot.AxisFlags_.no_label
                        | implot.AxisFlags_.lock | implot.AxisFlags_.no_grid_lines
                        | implot.AxisFlags_.no_tick_marks
                    )
                    y_axis_flags = (
                        implot.AxisFlags_.no_tick_labels | implot.AxisFlags_.no_label
                        | implot.AxisFlags_.lock | implot.AxisFlags_.no_grid_lines
                    )

                    implot.setup_axes(
                        '', '',
                        x_flags=x_axis_flags, y_flags=y_axis_flags
                    )
                    implot.setup_axes_limits(0, 1, 0, 1)

                    if plot_height:
                        spectrogram_data = self.get_spectrogram_data(
                            channel - 1,
                            self.implot_limits.x.min, self.implot_limits.x.max,
                            plot_width, plot_height,
                        )
                        if spectrogram_data is None:
                            spectrogram_data = np.full((1, 1), 0)

                        implot.push_colormap(implot.Colormap_.viridis)
                        implot.plot_heatmap(
                            "##chan_spectrogram",
                            spectrogram_data,
                            label_fmt='',
                            scale_min=-60, scale_max=12,
                            bounds_min=implot.Point(0, 0),
                            bounds_max=implot.Point(1, 1),
                            spec=implot.Spec(flags=0)
                        )
                        implot.pop_colormap()
                    implot.end_plot()
                    if imgui.is_item_hovered():
                        plot_hovered = True
                imgui.end_group()
                imgui.pop_id()

            if self.implot_playhead_needs_set:
                self.implot_playhead_needs_set = False

            if limits_changed:
                self.implot_limits_need_set = [True] * (num_channels + 1)
                self.implot_limits = limits_changed
                self.implot_limits_counter = limit_delay_frames

            if options_changed:
                MFPGUI().async_task(self.channel_options_update())

            implot.pop_style_var()
            implot.end_aligned_plots()

        self.implot_plot_hovered = plot_hovered
        imgui.end()

    def render_meter_bar(self, height, rms_value, peak_value):
        imgui.begin_group()
        imgui.dummy([10, 1])
        imgui.dummy([1, height-1])
        imgui.end_group()
        top_left = imgui.get_item_rect_min()
        bottom_right = imgui.get_item_rect_max()
        draw_list = imgui.get_window_draw_list()

        meter_max = 0
        meter_min = -40

        rms_db = min(meter_max, max(meter_min, 20*math.log10(max(0.000001, rms_value))))
        peak_db = min(meter_max, max(meter_min, 20*math.log10(max(0.000001, peak_value))))

        rms_fraction = (rms_db - meter_min) / (meter_max - meter_min)
        peak_fraction = (peak_db - meter_min) / (meter_max - meter_min)

        draw_list.add_rect_filled(
            top_left, bottom_right,
            ColorDB().backend.im_col32(ColorDB().find('default-fill-color-selected')),
            rounding=2,
        )
        draw_list.add_rect(
            top_left, bottom_right,
            ColorDB().backend.im_col32(ColorDB().find('default-stroke-color')),
            rounding=2,
            thickness=2,
        )
        draw_list.add_rect_filled(
            [top_left[0], bottom_right[1] - height * rms_fraction],
            bottom_right,
            ColorDB().backend.im_col32(ColorDB().find('meter-color-rms')),
            rounding=2,
        )

        draw_list.add_rect_filled(
            [top_left[0], bottom_right[1] - height * peak_fraction - 2],
            [bottom_right[0], bottom_right[1] - height*peak_fraction + 2],
            ColorDB().backend.im_col32(ColorDB().find('meter-color-peak')),
            rounding=2,
        )

    ########################################
    # render wrapper
    def render(self):
        keep_going = True

        imgui.set_next_window_size([
            self.app_window.window_width,
            self.app_window.console_panel_height - self.app_window.menu_height
        ])
        imgui.set_next_window_pos((
            0,
            self.app_window.window_height - self.app_window.console_panel_height
        ))

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
                | imgui.WindowFlags_.no_bring_to_front_on_focus
            )
        )

        if imgui.is_window_hovered(imgui.FocusedFlags_.child_windows):
            self.app_window.zone_hovered("bufedit")

        if self.needs_focus:
            imgui.set_window_focus()
            imgui.set_window_collapsed(False)
            self.needs_focus = False

        toolbar_height = self.render_toolbar()
        self.render_channels(toolbar_height)

        if self.implot_playhead_start_time:
            self.app_window.imgui_prevent_idle = 1

        imgui.end()

        # grab new data once per second
        if self.rec_recording:
            now = datetime.now()
            if (now - self.buffer_data_last_update).total_seconds() > 1:
                self.buffer_grab(self.working_buf_obj)

        imgui.pop_style_var(3)

        return keep_going

    ########################################
    # view control
    async def zoom_change(self, delta):
        orig_range = self.implot_limits.x.max - self.implot_limits.x.min
        delta_range = -0.5 * orig_range * delta
        self.implot_limits.x.max += delta_range
        self.implot_limits.x.min -= delta_range
        self.implot_limits_need_set = [True] * (self.buffer_info.channels + 1)

    async def zoom_to_selection(self):
        self.implot_limits.x.max = self.implot_selection.x.max
        self.implot_limits.x.min = self.implot_selection.x.min
        self.implot_limits_need_set = [True] * (self.buffer_info.channels + 1)

    async def playhead_center_view(self):
        vmin = self.implot_limits.x.min
        vmax = self.implot_limits.x.max
        cur_center = (vmax - vmin)*0.5 + vmin
        delta_center = self.implot_playhead - cur_center
        self.implot_limits.x.max = vmax + delta_center
        self.implot_limits.x.min = vmin + delta_center
        self.implot_limits_need_set = [True] * (self.buffer_info.channels + 1)

    def channel_options_rec_mask(self):
        mask = 0
        for channel, copt in enumerate(self.channel_options):
            mask = mask + (copt.get("rec", 0) << channel)
        return mask

    async def channel_options_update(self):
        """
        Update the working patch to reflect current selected options
        """
        from mfp.gui_main import MFPGUI
        rec_channels = self.channel_options_rec_mask()
        await MFPGUI().mfp.send(self.working_source_id, 0, dict(
            monitor_channels=rec_channels
        ))
        await MFPGUI().mfp.send(self.working_sink_id, 0, dict(
            monitor_channels=0xff,
            rec_channels=rec_channels
        ))

        self.rec_recording = self.rec_enabled and bool(rec_channels)

        solo_channels = False
        for channel, copt in enumerate(self.channel_options):
            solo = copt.get("solo")
            if solo:
                solo_channels = True

        for channel, copt in enumerate(self.channel_options):
            mute = copt.get("mute", False)
            solo = copt.get("solo", False)
            fx = copt.get("fx", True)

            gain_id = self.working_mon_gain[channel]

            if (
                (not solo_channels and not mute)
                or (solo and not mute)
            ):
                await MFPGUI().mfp.send(gain_id, 1, 1)
            else:
                await MFPGUI().mfp.send(gain_id, 1, 0)

            # crossfader to bypass wet FX chain for this channel
            if len(self.fx_patch_channel_enable) > channel:
                fx_id = self.fx_patch_channel_enable[channel]
                if fx and fx_id:
                    await MFPGUI().mfp.send(fx_id, 0, 1)
                else:
                    await MFPGUI().mfp.send(fx_id, 0, 0)


from . import buffer_ops
from . import clipboard_ops
from . import working_patch
from . import fx_patch
from . import spectrogram
from . import toolbar
from . import playhead
