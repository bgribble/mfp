"""
buffer_editor.py -- BufferEditor() class definition
"""
import asyncio
import os
from datetime import datetime
from posix_ipc import SharedMemory
import numpy as np
from imgui_bundle import implot, imgui
from mfp import log
from mfp.buffer_info import BufferInfo
from .app_window import menu_bar


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

        self.shm_obj = None
        self.buffer_source_info = None
        self.buffer_info = None
        self.buffer_data = None
        self.buffer_peaks = {}

        self.working_patch_id = None
        self.working_patch_info = None
        self.working_buf_id = None
        self.working_buf_obj = None
        self.working_source_id = None
        self.working_source_info = None
        self.working_sink_id = None
        self.working_sink_info = None

        self.fx_patch_id = None
        self.fx_patch_elements = {}

        self.channel_selections = [None]         # per-channel select box state (transient)
        self.channel_selections_active = [False]  # per-channel select box activity

    def focus(self):
        self.needs_focus = True

    async def close(self):
        await self.close_working_patch()

    def set_playhead_at_pointer(self):
        self.implot_playhead_needs_set = True

    async def init_working_patch(self):
        from mfp.gui_main import MFPGUI
        if self.working_patch_id:
            self.close_working_patch()

        self.working_patch_id = await MFPGUI().mfp.open_file(None, show_gui=False)
        self.working_patch_info = await MFPGUI().mfp.get_tooltip_info(self.working_patch_id, details=True)
        buffer_params = dict(
            channels=self.buffer_info.channels + 2,
            size=self.buffer_info.size,
        )

        self.working_source_info = await MFPGUI().mfp.create(
            "buffer~",
            ", ".join([f"{key}={value!r}" for key, value in buffer_params.items()]),
            self.working_patch_info.get("name"),
            None,
            "source_buffer"
        )
        self.working_source_id = self.working_source_info.get("obj_id")

        # wait for buffer to be initialized
        source = None
        while source is None:
            try:
                all_buffers = await MFPGUI().mfp.get_buffer_info()
                source = next(b for b in all_buffers if b.get("proc_name") == "source_buffer")
            except StopIteration:
                await asyncio.sleep(0.1)

        source_buf = source.get("buf_info")
        self.working_buf_id = source_buf.buf_id
        self.working_buf_obj = SharedMemory(source_buf.buf_id)
        buffer_params["buf_id"] = source_buf.buf_id
        buffer_params["channels"] = source_buf.channels
        buffer_params["size"] = source_buf.size

        self.working_sink_info = await MFPGUI().mfp.create(
            "buffer~",
            ", ".join([f"{key}={value!r}" for key, value in buffer_params.items()]),
            self.working_patch_info.get("name"),
            None,
            "sink_buffer"
        )
        self.working_sink_id = self.working_sink_info.get("obj_id")

        self.working_aud0_info = await MFPGUI().mfp.create(
            "out~", "0", self.working_patch_info.get("name"), None, "audition 0"
        )
        self.working_aud1_info = await MFPGUI().mfp.create(
            "out~", "1", self.working_patch_info.get("name"), None, "audition 1"
        )
        await MFPGUI().mfp.connect(self.working_sink_id, 0, self.working_aud0_info.get("obj_id"), 0)
        await MFPGUI().mfp.connect(self.working_sink_id, 1, self.working_aud1_info.get("obj_id"), 0)

        self.buffer_sync(self.shm_obj, self.buffer_info, self.working_buf_obj, source_buf)
        self.buffer_compute_peaks()

    async def close_working_patch(self):
        from mfp.gui_main import MFPGUI

        if self.working_patch_id:
            await MFPGUI().mfp.delete(self.working_patch_id)
            self.working_patch_id = None

    ########################################
    # fx patch
    async def fx_open_patch(self, fxname):
        from mfp.gui_main import MFPGUI

        # create new patch wrapping the specified effect
        self.fx_patch_id = await MFPGUI().mfp.open_file(
            "bufedit.fx~.mfp",
            initargs=f"'{fxname}', {self.buffer_info.channels}",
            show_gui=True,
        )

        # each fx patch needs to take a number param for channel count
        # input level and xfade channels on the left

        # connect source to fx
        for port in range(self.buffer_info.channels):
            await MFPGUI().mfp.connect(
                self.working_source_id, port, self.fx_patch_id, port + 2
            )
            await MFPGUI().mfp.connect(
                self.fx_patch_id, port, self.working_sink_id, port
            )

            if port % 2 == 0:
                # disconnect previous outputs
                await MFPGUI().mfp.disconnect(
                    self.working_sink_id, port, self.working_aud0_info.get("obj_id"), 0
                )
                await MFPGUI().mfp.connect(
                    self.fx_patch_id, port, self.working_aud0_info.get("obj_id"), 0
                )
            else:
                await MFPGUI().mfp.disconnect(
                    self.working_sink_id, port, self.working_aud1_info.get("obj_id"), 0
                )
                await MFPGUI().mfp.connect(
                    self.fx_patch_id, port, self.working_aud1_info.get("obj_id"), 0
                )

        # connect input level and xfade
        for port in [0, 1]:
            await MFPGUI().mfp.connect(
                self.working_source_id, self.buffer_info.channels + port,
                self.fx_patch_id, port
            )

        for element in [
            'apply_button', 'cancel_button', 'selection_toggle',
            'bypass_toggle', 'xfade_enum', 'preroll_enum'
        ]:
            element_id = await MFPGUI().mfp.resolve(element, self.fx_patch_id)
            self.fx_patch_elements[element] = MFPGUI().objects.get(element_id)

        # add actions for Apply and Cancel buttons
        cancel = self.fx_patch_elements["cancel_button"]
        cancel.extra_action = self.fx_close_patch

        apply = self.fx_patch_elements["apply_button"]
        apply.extra_action = self.fx_apply_patch

    async def fx_apply_patch(self):
        from mfp.gui_main import MFPGUI
        rec_channels = sum(
            1 << c for c in range(self.buffer_info.channels)
        )

        source_params = dict(
            buf_mode=5,
            play_channels=0xff,
            buf_pos=0,
            region_start=0,
            region_end=self.buffer_info.size,
            trig_trigger=1,
        )
        sink_params = dict(
            buf_mode=0,
            play_channels=0,
            rec_channels=rec_channels,
            rec_enabled=1,
            buf_pos=0,
            region_start=0,
            region_end=self.buffer_info.size,
            trig_trigger=1,
        )
        await MFPGUI().mfp.send(self.working_source_id, 0, source_params)
        await MFPGUI().mfp.send(self.working_sink_id, 0, sink_params)

        log.debug(f"[bufedit] calling freewheel_context")
        await MFPGUI().mfp.freewheel_context(self.fx_patch_id, self.buffer_info.size)

    async def fx_close_patch(self):
        from mfp.gui_main import MFPGUI

        # remove actions for Apply and Cancel buttons
        cancel = self.fx_patch_elements["cancel_button"]
        cancel.extra_action = None

        # reconnect sink buffer to audition outs, disconnect FX outs
        for port in range(self.buffer_info.channels):
            await MFPGUI().mfp.disconnect(
                self.working_source_id, port,
                self.fx_patch_id, port + 2
            )
            await MFPGUI().mfp.disconnect(
                self.fx_patch_id, port,
                self.working_sink_id, port
            )

            if port % 2 == 0:
                # reconnect previous outputs
                await MFPGUI().mfp.connect(
                    self.working_sink_id, port, self.working_aud0_info.get("obj_id"), 0
                )
                await MFPGUI().mfp.disconnect(
                    self.fx_patch_id, port, self.working_aud0_info.get("obj_id"), 0
                )
            else:
                await MFPGUI().mfp.connect(
                    self.working_sink_id, port, self.working_aud1_info.get("obj_id"), 0
                )
                await MFPGUI().mfp.disconnect(
                    self.fx_patch_id, port, self.working_aud1_info.get("obj_id"), 0
                )

        # connect input level and xfade
        for port in [0, 1]:
            await MFPGUI().mfp.disconnect(
                self.working_source_id, self.buffer_info.channels + port,
                self.fx_patch_id, port
            )

        # delete FX patch
        await MFPGUI().mfp.delete(self.fx_patch_id)
        self.fx_patch_id = None

    ########################################
    # buffer operations
    def buffer_grab(self):
        def offset(channel):
            return channel * self.buffer_info.size * self.FLOAT_SIZE
        if self.buffer_info is None:
            return None
        if self.shm_obj is None:
            self.shm_obj = SharedMemory(self.buffer_info.buf_id)

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
        except Exception as e:
            log.debug("[grab]: error grabbing data", e)
            import traceback
            traceback.print_exc()
            return None
        self.buffer_compute_peaks()

    def buffer_sync(self, from_obj, from_info, to_obj, to_info, data=None):
        sync_channels = to_info.channels
        if from_info:
            sync_channels = min(from_info.channels, to_info.channels)
        for c in range(sync_channels):
            self.buffer_sync_channel(c, from_obj, from_info, to_obj, to_info, data)

    def buffer_sync_channel(self, channel, from_obj, from_info, to_obj, to_info, data=None):
        def offset(buf_info, channel):
            return channel * buf_info.size * self.FLOAT_SIZE

        if from_obj:
            os.lseek(from_obj.fd, offset(from_info, channel), os.SEEK_SET)
            slc = os.read(from_obj.fd, int(from_info.size * self.FLOAT_SIZE))
        elif data is not None:
            slc = data.tobytes()
        else:
            slc = self.buffer_data[channel].tobytes()

        os.lseek(to_obj.fd, offset(to_info, channel), os.SEEK_SET)
        os.write(to_obj.fd, slc)

    def buffer_compute_peaks(self):
        self.buffer_peaks = {}
        padding = 10 - len(self.buffer_data[0]) % 10
        padded = [
            np.pad(chan, (0, padding), mode='constant')
            for chan in self.buffer_data
        ]
        total_time = len(padded[0]) / self.buffer_info.rate
        sample_time = 1/self.buffer_info.rate
        self.implot_total_time = total_time
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

    def buffer_set_selection(self):
        preroll = 0
        xfade = 0

        if "preroll_enum" in self.fx_patch_elements:
            preroll = self.fx_patch_elements.get('preroll_enum').value
            xfade = self.fx_patch_elements.get('xfade_enum').value

        working_buf_info = BufferInfo(
            buf_id=self.working_buf_id,
            size=self.buffer_info.size,
            channels=self.buffer_info.channels + 2,
            rate=self.buffer_info.rate,
            offset=self.buffer_info.offset
        )
        # input level signal
        startpos = int(
            (self.implot_selection.x.min - (preroll / 1000.0)) * self.buffer_info.rate
        )
        endpos = int(
            (self.implot_selection.x.max + (preroll / 1000.0)) * self.buffer_info.rate
        )

        startpos = max(0, startpos)
        endpos = min(self.buffer_info.size, endpos)

        input_arr = np.zeros(self.buffer_info.size, dtype=np.float32)
        input_arr[startpos:endpos] = 1
        self.buffer_sync_channel(
            self.buffer_info.channels, None, None, self.working_buf_obj, working_buf_info,
            data=input_arr
        )

        # crossfade signal
        inramp_start = int(self.implot_selection.x.min * self.buffer_info.rate)
        outramp_end = int(self.implot_selection.x.max * self.buffer_info.rate)

        ramp_len = min(
            int((xfade / 1000) * self.buffer_info.rate),
            int((outramp_end - inramp_start) / 2)
        )

        inramp_end = inramp_start + ramp_len
        outramp_start = outramp_end - ramp_len

        xfade_arr = np.zeros(self.buffer_info.size, dtype=np.float32)
        xfade_arr[inramp_start:outramp_end] = 1
        xfade_arr[inramp_start:inramp_end] = np.linspace(0, 1, ramp_len, dtype=np.float32)
        xfade_arr[outramp_start:outramp_end] = np.linspace(1, 0, ramp_len, dtype=np.float32)

        self.buffer_sync_channel(
            self.buffer_info.channels + 1, None, None, self.working_buf_obj, working_buf_info,
            data=xfade_arr
        )

    ########################################
    # toolbar
    def render_toolbar(self):
        from mfp.gui import image_utils
        from mfp.gui_main import MFPGUI
        line_height = imgui.get_text_line_height()
        button_size = 1.25*line_height

        imgui.set_next_window_size((self.app_window.window_width, 2 * button_size))
        imgui.set_next_window_pos(imgui.get_window_pos())

        play_tex = image_utils.load_texture_from_file("icons/media-playback-start.png")
        pause_tex = image_utils.load_texture_from_file("icons/media-playback-pause.png")
        stop_tex = image_utils.load_texture_from_file("icons/media-playback-stop.png")
        home_tex = image_utils.load_texture_from_file("icons/media-skip-backward.png")
        end_tex = image_utils.load_texture_from_file("icons/media-skip-forward.png")
        record_tex = image_utils.load_texture_from_file("icons/media-record.png")
        loop_tex = image_utils.load_texture_from_file("icons/view-refresh.png")
        menu_tex = image_utils.load_texture_from_file("icons/open-menu.png")
        zoom_in_tex = image_utils.load_texture_from_file("icons/zoom-in.png")
        zoom_out_tex = image_utils.load_texture_from_file("icons/zoom-out.png")
        zoom_fit_tex = image_utils.load_texture_from_file("icons/zoom-fit-best.png")
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
        padding = (0.25 * button_size, 0.25 * button_size)
        imgui.push_style_var(imgui.StyleVar_.frame_padding, padding)
        imgui.push_style_var(imgui.StyleVar_.item_spacing, padding)

        imgui.set_cursor_pos(padding)

        #######################
        # transport control

        if imgui.image_button(
            "##pause_btn", imgui.ImTextureRef(pause_tex[0]), [button_size, button_size]
        ):
            MFPGUI().async_task(self.playhead_pause())
        imgui.same_line()

        if imgui.image_button(
            "##play_btn", imgui.ImTextureRef(play_tex[0]), [button_size, button_size]
        ):
            MFPGUI().async_task(self.playhead_start())
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
            MFPGUI().async_task(self.playhead_move(self.implot_limits.x.max - 0.001))

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
            imgui.set_tooltip("Jump to playhead")
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

        imgui.pop_style_var(2)
        menu_bar.render_bufedit_menu(self.app_window)
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

        binfo = self.buffer_source_info
        fname = binfo.get('file_name') or 'No file'
        ttime = self.buffer_info.size / self.buffer_info.rate
        display_name = f"{binfo.get('proc_name')} ({fname}) channels={self.buffer_info.channels}"
        imgui.begin(
            f"{display_name} time={ttime:.1f}s frames={self.buffer_info.size}##channelsview",
            flags=(
                imgui.WindowFlags_.no_collapse
                | imgui.WindowFlags_.no_resize
                | imgui.WindowFlags_.no_saved_settings
                | imgui.WindowFlags_.no_move
            )
        )
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
            self.app_window.selected_window = "bufedit"
            self.app_window.enable_buffer_editor_input()

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
