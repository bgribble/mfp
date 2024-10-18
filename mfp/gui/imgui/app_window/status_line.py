from imgui_bundle import imgui, imgui_node_editor as nedit

CHAR_PIXELS = 10

def render(app_window):
    imgui.set_next_window_size((app_window.window_width, app_window.menu_height + 5))
    imgui.set_next_window_pos((0, app_window.window_height - app_window.menu_height -5 ))
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
        right_corner_text = f"FPS: {fps} Pointer: ({app_window.input_mgr.pointer_ev_x}, {app_window.input_mgr.pointer_ev_y})"
        cur = imgui.get_cursor_pos()
        imgui.set_cursor_pos((
            app_window.window_width - len(right_corner_text) * CHAR_PIXELS,
            cur[1]
        ))
        imgui.text(right_corner_text)

    imgui.end()
