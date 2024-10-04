from imgui_bundle import imgui, imgui_node_editor as nedit


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
        elapsed = (app_window.frame_timestamps[-1] - app_window.frame_timestamps[0]).total_seconds()
        imgui.text(f"FPS: {int((len(app_window.frame_timestamps)-1) / elapsed)}")
        imgui.same_line()
        imgui.text(f"Zoom: {(1.0/nedit.get_current_zoom()):0.2f}")

    imgui.end()
