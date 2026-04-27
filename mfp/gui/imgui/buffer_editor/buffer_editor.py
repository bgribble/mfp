"""
buffer_editor.py -- BufferEditor() class definition
"""
from datetime import datetime
from imgui_bundle import implot, imgui
from mfp import log


def fmt_time(ttime):
    minutes = int(ttime // 60)
    seconds = int(ttime - 60*minutes)
    sfrac = int(1000 * (ttime % 1.0))
    return f"{minutes:02d}:{seconds:02d}.{sfrac:03d}"


def unfmt_time(strtime):
    import re
    matches = re.match(r"^([0-9]+):([0-9.]+)$", strtime)
    try:
        return 60 * float(matches.group(1)) + float(matches.group(2))
    except Exception:
        return None


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
        self.implot_playhead_start_time = None
        self.implot_playhead_start_pos = None
        self.implot_playhead_looping = False
        self.implot_total_time = 0

        self.all_buffers = []

        self.shm_obj = None                  # primary (original) buffer
        self.buffer_source_info = None
        self.buffer_info = None
        self.buffer_data = None
        self.buffer_peaks = {}

        self.working_patch_id = None
        self.working_patch_info = None
        self.working_buf_id = None
        self.working_buf_obj = None          # working buffer, shared btw source/sink
        self.working_buf_info = None
        self.working_source_id = None
        self.working_source_info = None
        self.working_sink_id = None
        self.working_sink_info = None

        self.fx_patch_id = None
        self.fx_patch_elements = {}

        self.channel_selections = [None]         # per-channel select box state (transient)
        self.channel_selections_active = [False]  # per-channel select box activity

        self.clipboard_data = None
        self.clipboard_size = None
        self.clipboard_pos = None

    def focus(self):
        self.needs_focus = True

    async def close(self):
        await self.close_working_patch()

    def set_playhead_at_pointer(self):
        self.implot_playhead_needs_set = True

    ########################################
    # toolbar
    def render_toolbar(self):
        from mfp.gui import image_utils
        from mfp.gui_main import MFPGUI
        from . import menu_button

        line_height = imgui.get_text_line_height()
        button_size = 1.25*line_height

        imgui.set_next_window_size((self.app_window.window_width, 2 * button_size))
        imgui.set_next_window_pos(imgui.get_window_pos())

        play_tex = image_utils.load_texture_from_file("icons/playback-start.png")
        pause_tex = image_utils.load_texture_from_file("icons/playback-pause.png")
        stop_tex = image_utils.load_texture_from_file("icons/playback-stop.png")
        home_tex = image_utils.load_texture_from_file("icons/rewind.png")
        end_tex = image_utils.load_texture_from_file("icons/fast-forward.png")
        record_tex = image_utils.load_texture_from_file("icons/record.png")
        loop_tex = image_utils.load_texture_from_file("icons/playback-loop.png")
        menu_tex = image_utils.load_texture_from_file("icons/open-menu.png")
        zoom_in_tex = image_utils.load_texture_from_file("icons/zoom-in.png")
        zoom_out_tex = image_utils.load_texture_from_file("icons/zoom-out.png")
        zoom_fit_tex = image_utils.load_texture_from_file("icons/zoom-to-selection.png")
        center_playhead_tex = image_utils.load_texture_from_file("icons/center-playhead.png")

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
            self.app_window.zone_hovered("bufedit")

        padding = (0.25 * button_size, 0.25 * button_size)
        imgui.push_style_var(imgui.StyleVar_.frame_padding, padding)
        imgui.push_style_var(imgui.StyleVar_.item_spacing, padding)

        imgui.set_cursor_pos(padding)

        imgui.push_style_color(
            imgui.Col_.button, [0.75, 0.75, 0.75, 1]
        )
        imgui.push_style_color(
            imgui.Col_.button_hovered, [0.9, 0.9, 0.9, 1]
        )
        imgui.push_style_color(
            imgui.Col_.button_active, [1, 1, 1, 1]
        )

        #######################
        # transport control
        if imgui.image_button(
            "##pause_btn", imgui.ImTextureRef(pause_tex[0]),
            [button_size, button_size]
        ):
            MFPGUI().async_task(self.playhead_pause())
        imgui.same_line()

        if self.implot_playhead_start_time:
            imgui.push_style_color(
                imgui.Col_.button, [0.6, 0.75, 0.6, 1]
            )
            imgui.push_style_color(
                imgui.Col_.button_hovered, [0.7, 0.9, 0.7, 1]
            )
        if imgui.image_button(
            "##play_btn", imgui.ImTextureRef(play_tex[0]), [button_size, button_size]
        ):
            MFPGUI().async_task(self.playhead_start())
        if self.implot_playhead_start_time:
            imgui.pop_style_color(2)

        imgui.same_line()

        if imgui.image_button(
            "##stop_btn", imgui.ImTextureRef(stop_tex[0]), [button_size, button_size]
        ):
            MFPGUI().async_task(self.playhead_pause())
        imgui.same_line()

        if imgui.image_button(
            "##home_btn", imgui.ImTextureRef(home_tex[0]), [button_size, button_size]
        ):
            MFPGUI().async_task(self.playhead_move(0))
        imgui.same_line()

        if imgui.image_button(
            "##end_btn", imgui.ImTextureRef(end_tex[0]), [button_size, button_size]
        ):
            MFPGUI().async_task(self.playhead_move(self.implot_total_time - 0.001))

        imgui.same_line()

        if imgui.image_button(
            "##record_btn", imgui.ImTextureRef(record_tex[0]), [button_size, button_size]
        ):
            pass
        imgui.same_line()

        if not self.implot_selection:
            imgui.begin_disabled()

        if imgui.image_button(
            "##loop_btn", imgui.ImTextureRef(loop_tex[0]), [button_size, button_size]
        ):
            MFPGUI().async_task(self.playhead_loop_selection())
        imgui.same_line()

        if not self.implot_selection:
            imgui.end_disabled()

        imgui.dummy((button_size, 1))
        imgui.same_line()

        #######################
        # zoom

        if imgui.image_button(
            "##zoom_in_btn", imgui.ImTextureRef(zoom_in_tex[0]), [button_size, button_size]
        ):
            MFPGUI().async_task(self.zoom_change(0.25))

        if imgui.is_item_hovered():
            imgui.set_tooltip("Zoom in")
        imgui.same_line()

        if imgui.image_button(
            "##zoom_out_btn", imgui.ImTextureRef(zoom_out_tex[0]), [button_size, button_size]
        ):
            MFPGUI().async_task(self.zoom_change(-0.25))
        if imgui.is_item_hovered():
            imgui.set_tooltip("Zoom out")
        imgui.same_line()

        if not self.implot_selection:
            imgui.begin_disabled()

        if imgui.image_button(
            "##zoom_selection_btn", imgui.ImTextureRef(zoom_fit_tex[0]), [button_size, button_size]
        ):
            MFPGUI().async_task(self.zoom_to_selection())
        if imgui.is_item_hovered() and self.implot_selection:
            imgui.set_tooltip("Zoom to selection")
        imgui.same_line()

        if not self.implot_selection:
            imgui.end_disabled()

        if imgui.image_button(
            "##center_playhead_btn", imgui.ImTextureRef(center_playhead_tex[0]), [button_size, button_size]
        ):
            MFPGUI().async_task(self.playhead_center_view())
        if imgui.is_item_hovered():
            imgui.set_tooltip("Center playhead")
        imgui.same_line()

        imgui.dummy((button_size, 1))
        imgui.same_line()

        #######################
        # playhead and selection info

        imgui.begin_group()
        imgui.dummy((0.1, 0.125 * line_height))
        imgui.text("Pos:")
        imgui.end_group()
        imgui.same_line()
        imgui.push_font(self.app_window.imgui_default_font, 18)
        imgui.push_style_var(imgui.StyleVar_.window_border_size, 1)
        imgui.set_next_item_width(6 * line_height)
        orig_ph = fmt_time(self.implot_playhead or 0)
        ph_changed, new_ph = imgui.input_text(
            "##playhead_pos", orig_ph
        )
        if ph_changed:
            new_time = unfmt_time(new_ph)
            if new_time is not None:
                MFPGUI().async_task(self.playhead_move(new_time))
        imgui.pop_style_var()
        imgui.pop_font()
        imgui.same_line()

        if not self.implot_selection:
            imgui.begin_disabled()

        imgui.begin_group()
        imgui.dummy((0.1, 0.125 * line_height))
        imgui.text("Sel:")
        imgui.end_group()
        imgui.same_line()
        imgui.push_font(self.app_window.imgui_default_font, 18)
        imgui.push_style_var(imgui.StyleVar_.window_border_size, 1)

        imgui.set_next_item_width(6 * line_height)
        ss_changed, ss_new = imgui.input_text(
            "##selection_start_pos",
            fmt_time(self.implot_selection.x.min if self.implot_selection else 0)
        )
        if ss_changed:
            new_time = unfmt_time(ss_new)
            if new_time is not None:
                MFPGUI().async_task(
                    self.playhead_set_selection(new_time, None)
                )
        imgui.same_line()
        imgui.text("-")
        imgui.same_line()
        imgui.set_next_item_width(6 * line_height)
        se_changed, se_new = imgui.input_text(
            "##selection_end_pos",
            fmt_time(self.implot_selection.x.max if self.implot_selection else 0)
        )
        if se_changed:
            new_time = unfmt_time(se_new)
            if new_time is not None:
                MFPGUI().async_task(
                    self.playhead_set_selection(None, new_time)
                )
        imgui.pop_style_var()
        imgui.pop_font()
        imgui.same_line()

        if not self.implot_selection:
            imgui.end_disabled()

        #######################
        # menu on far right

        imgui.dummy((
            imgui.get_window_width() - imgui.get_cursor_pos()[0] - 2*button_size,
            button_size
        ))
        imgui.same_line()

        if imgui.image_button(
            "##menu_button", imgui.ImTextureRef(menu_tex[0]), [button_size, button_size]
        ):
            imgui.open_popup("##bufedit_popup")

        imgui.pop_style_color(3)
        imgui.pop_style_var(2)
        menu_button.render_bufedit_menu(self.app_window)
        imgui.end()
        return 2 * button_size

    ########################################
    # plots
    def render_channels(self, toolbar_height):
        from mfp.gui_main import MFPGUI
        implot.set_current_context(self.implot_context)

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
        fname = binfo.file_name or 'No file'
        #log.debug(f"[render] binfo={binfo}")
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
                if self.implot_playhead_looping:
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

            for channel in range(num_channels + 1):
                imgui.push_id(str(channel))
                if channel == 0:
                    height = line_height * 4
                    plot_flags = implot.Flags_.no_mouse_text
                    x_axis_flags = implot.AxisFlags_.no_label
                    y_axis_flags = implot.AxisFlags_.no_tick_labels | implot.AxisFlags_.no_label
                else:
                    height = line_height * 6
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
                            MFPGUI().async_task(self.playhead_move(pointer[0]))

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
                            MFPGUI().async_task(
                                self.playhead_update_selection()
                            )

                    # playhead
                    implot.drag_line_x(0, self.implot_playhead, [1, 1, 1, 1])

                    if chan_sel.x.min not in (0, chan_sel.x.max):
                        self.implot_selection = chan_sel
                        self.channel_selections[channel] = chan_sel
                        self.channel_selections_active[channel] = True
                        MFPGUI().async_task(
                            self.playhead_update_selection()
                        )
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

    ########################################
    # playhead control
    async def playhead_start(self):
        from mfp.gui_main import MFPGUI
        pos_samples = self.implot_playhead * self.buffer_info.rate

        buffer_params = dict(
            buf_mode=5,
            play_channels=0xff,
            rec_channels=0,
            rec_enabled=0,
            buf_pos=pos_samples,
            region_start=pos_samples,
            region_end=self.implot_total_time * self.buffer_info.rate
        )

        await MFPGUI().mfp.send(self.working_sink_id, 0, buffer_params)
        await MFPGUI().mfp.send(self.working_source_id, 0, buffer_params)
        await MFPGUI().mfp.send_bang(self.working_sink_id, 0)
        await MFPGUI().mfp.send_bang(self.working_source_id, 0)

        self.implot_playhead_start_time = datetime.now()
        self.implot_playhead_start_pos = self.implot_playhead
        self.implot_playhead_looping = False

    async def playhead_move(self, new_pos):
        from mfp.gui_main import MFPGUI
        self.implot_playhead = new_pos
        pos_samples = self.implot_playhead * self.buffer_info.rate

        buffer_params = dict(
            buf_pos=pos_samples
        )

        await MFPGUI().mfp.send(self.working_sink_id, 0, buffer_params)
        await MFPGUI().mfp.send(self.working_source_id, 0, buffer_params)

        if self.implot_playhead_start_time:
            self.implot_playhead_start_time = datetime.now()
            self.implot_playhead_start_pos = self.implot_playhead

    async def playhead_pause(self):
        from mfp.gui_main import MFPGUI
        buffer_params = dict(
            buf_state=0,
            rec_enabled=0,
        )

        await MFPGUI().mfp.send(self.working_sink_id, 0, buffer_params)
        await MFPGUI().mfp.send(self.working_source_id, 0, buffer_params)

        self.implot_playhead_start_time = None
        self.implot_playhead_looping = False

    async def playhead_set_selection(self, sel_start, sel_end):
        if not self.implot_selection:
            self.implot_selection = implot.Rect(
                0, 0, -1, 1
            )
        if sel_start is not None:
            self.implot_selection.x.min = sel_start
        if sel_end is not None:
            self.implot_selection.x.max = sel_end

        return await self.playhead_update_selection()

    async def playhead_update_selection(self):
        from mfp.gui_main import MFPGUI
        start_samples = self.implot_selection.x.min * self.buffer_info.rate
        end_samples = self.implot_selection.x.max * self.buffer_info.rate
        buffer_params = dict(
            region_start=start_samples,
            region_end=end_samples
        )
        if self.implot_playhead_looping:
            if self.implot_playhead < self.implot_selection.x.min:
                self.implot_playhead = self.implot_selection.x.min
                buffer_params['buf_pos'] = self.implot_playhead * self.buffer_info.rate
            elif self.implot_playhead >= self.implot_selection.x.max:
                self.implot_playhead = self.implot_selection.x.max
                buffer_params['buf_pos'] = self.implot_playhead * self.buffer_info.rate

        if self.implot_playhead_start_time:
            self.implot_playhead_start_time = datetime.now()
            self.implot_playhead_start_pos = self.implot_playhead

        self.buffer_set_selection()

        await MFPGUI().mfp.send(self.working_sink_id, 0, buffer_params)
        await MFPGUI().mfp.send(self.working_source_id, 0, buffer_params)

    async def playhead_loop_selection(self):
        from mfp.gui_main import MFPGUI
        start_samples = self.implot_selection.x.min * self.buffer_info.rate
        end_samples = self.implot_selection.x.max * self.buffer_info.rate
        self.implot_playhead = self.implot_selection.x.min
        self.implot_playhead_looping = True

        buffer_params = dict(
            buf_mode=6,
            play_channels=0xff,
            rec_channels=0,
            buf_pos=start_samples,
            region_start=start_samples,
            region_end=end_samples
        )

        await MFPGUI().mfp.send(self.working_sink_id, 0, buffer_params)
        await MFPGUI().mfp.send(self.working_source_id, 0, buffer_params)
        await MFPGUI().mfp.send_bang(self.working_sink_id, 0)
        await MFPGUI().mfp.send_bang(self.working_source_id, 0)

        self.implot_playhead_start_time = datetime.now()
        self.implot_playhead_start_pos = self.implot_playhead

from . import buffer_ops
from . import clipboard_ops
from . import working_patch
from . import fx_patch

