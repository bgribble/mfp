from datetime import datetime

from imgui_bundle import imgui
from mfp import log
from mfp.gui.modes.global_mode import GlobalMode
from imgui_bundle import portable_file_dialogs as pfd

CHAR_PIXELS = 7


def render(app_window):
    imgui.set_next_window_size((app_window.window_width, app_window.menu_height + 8))
    imgui.set_next_window_pos((0, app_window.window_height - app_window.menu_height - 8))

    imgui.begin(
        "status_line",
        flags=(
            imgui.WindowFlags_.no_collapse
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_title_bar
            | imgui.WindowFlags_.no_decoration
        ),
    )

    if app_window.cmd_prompt:
        if imgui.is_window_hovered(imgui.FocusedFlags_.child_windows):
            app_window.selected_window = "canvas"
            if not isinstance(app_window.input_mgr.global_mode, GlobalMode):
                app_window.input_mgr.global_mode = GlobalMode(app_window)
                app_window.input_mgr.major_mode.enable()
                app_window.input_mgr.enable_minor_mode(app_window.cmd_manager.mode)

        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 3.0))
        imgui.text(app_window.cmd_prompt)

        imgui.same_line()
        window_w = imgui.get_window_width()
        imgui.push_item_width(-1)
        app_window.cmd_input.render()
        imgui.pop_item_width()

        if app_window.cmd_input_filename:
            imgui.same_line()
            cursor_x, cursor_y = imgui.get_cursor_pos()
            imgui.set_cursor_pos([window_w - 100, cursor_y])
            imgui.push_id("file_select")
            if imgui.button("Select..."):
                if app_window.cmd_input_filename == "open":
                    app_window.cmd_file_dialog = pfd.open_file("Select file")
                elif app_window.cmd_input_filename == "save":
                    app_window.cmd_file_dialog = pfd.save_file("Save as")
                elif app_window.cmd_input_filename == "folder":
                    app_window.cmd_file_dialog = pfd.select_filder("Select folder")
            imgui.pop_id()

        if app_window.cmd_file_dialog is not None and app_window.cmd_file_dialog.ready():
            results = app_window.cmd_file_dialog.result()
            app_window.cmd_file_dialog = None
            if results:
                app_window.cmd_input.set_text(results[0])

        imgui.pop_style_var()
        imgui.end()
        return

    if (
        app_window.cmd_hud_text
        and app_window.cmd_hud_expiry
        and app_window.cmd_hud_expiry > datetime.now()
    ):
        imgui.text(app_window.cmd_hud_text)
        imgui.end()
        return

    if len(app_window.frame_timestamps) > 1:
        if app_window.input_mgr and app_window.input_mgr.major_mode:
            mgr = app_window.input_mgr
            mode_label = f"{mgr.global_mode.short_description} > {mgr.major_mode.short_description}"
            minor = ','.join(
                [m.short_description for m in reversed(mgr.minor_modes)]
            )
            imgui.text(
                f"{mode_label}{' > ' if minor else ''}{minor}"
            )
            imgui.same_line()
            imgui.text(f" ({app_window.selected_window})")
            imgui.same_line()

        elapsed = (app_window.frame_timestamps[-1] - app_window.frame_timestamps[0]).total_seconds()
        fps = int((len(app_window.frame_timestamps)-1) / elapsed)

        fps_text = f"FPS: {fps}"
        dsp_text = ''
        if app_window.dsp_info:
            dsp_info = app_window.dsp_info
            srate = dsp_info.get("samplerate")
            latency_in = dsp_info.get("latency_in")
            latency_out = dsp_info.get("latency_out")
            channels_in = dsp_info.get("channels_in")
            channels_out = dsp_info.get("channels_out")
            dsp_text = f"DSP: {srate},io={channels_in}/{channels_out}"

        right_corner_text = ' '.join([
            fps_text, dsp_text
        ])
        cur = imgui.get_cursor_pos()
        imgui.set_cursor_pos((
            app_window.window_width - len(right_corner_text) * CHAR_PIXELS - 24,
            cur[1]
        ))
        imgui.text(right_corner_text)

    imgui.end()
