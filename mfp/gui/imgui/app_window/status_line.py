from imgui_bundle import imgui, imgui_node_editor as nedit

CHAR_PIXELS = 10

def render(app_window):
    imgui.set_next_window_size((app_window.window_width, app_window.menu_height))
    imgui.set_next_window_pos((0, app_window.window_height - app_window.menu_height))
    imgui.begin(
        "status_line",
        flags=(
            imgui.WindowFlags_.no_collapse
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_title_bar
            | imgui.WindowFlags_.no_decoration
        ),
    )

    if len(app_window.frame_timestamps) > 1:
        if app_window.input_mgr and app_window.input_mgr.major_mode:
            imgui.text(app_window.input_mgr.major_mode.short_description)
            imgui.same_line()

        elapsed = (app_window.frame_timestamps[-1] - app_window.frame_timestamps[0]).total_seconds()
        fps = int((len(app_window.frame_timestamps)-1) / elapsed)
        right_corner_text = f"FPS: {fps} Zoom: {(1.0/nedit.get_current_zoom()):0.2f}"
        cur = imgui.get_cursor_pos()
        imgui.set_cursor_pos((
            app_window.window_width - len(right_corner_text) * CHAR_PIXELS,
            cur[1]
        ))
        imgui.text(right_corner_text)

    imgui.end()
