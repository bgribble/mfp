from imgui_bundle import imgui

from mfp.gui.modes.console_mode import ConsoleMode


def render(app_window):
    imgui.begin(
        "console_panel",
        flags=(
            imgui.WindowFlags_.no_collapse
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_title_bar
        ),
    )
    if imgui.is_window_hovered(imgui.FocusedFlags_.child_windows):
        app_window.selected_window = "console"
        if not isinstance(app_window.input_mgr.global_mode, ConsoleMode):
            app_window.input_mgr.global_mode = ConsoleMode(app_window)
            app_window.input_mgr.major_mode.disable()
            for m in list(app_window.input_mgr.minor_modes):
                app_window.input_mgr.disable_minor_mode(m)

    if imgui.begin_tab_bar("console_tab_bar", imgui.TabBarFlags_.none):
        if imgui.begin_tab_item("Log")[0]:
            imgui.input_text_multiline(
                'log_output_text',
                app_window.log_text,
                (app_window.window_width, app_window.console_panel_height - app_window.menu_height),
                imgui.InputTextFlags_.read_only
            )
            imgui.end_tab_item()
        if imgui.begin_tab_item("Console")[0]:
            app_window.console_manager.render(
                app_window.window_width,
                app_window.console_panel_height - app_window.menu_height
            )
            imgui.end_tab_item()
        imgui.end_tab_bar()

    imgui.end()
