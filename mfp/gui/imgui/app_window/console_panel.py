import re
from datetime import datetime

from imgui_bundle import imgui

from mfp.gui.modes.console_mode import ConsoleMode


def filter_logs(filter_text, raw_log):
    filtered = []
    try:
        filter_re = re.compile(filter_text)
    except Exception:
        return raw_log

    for entry in raw_log.split('\n'):
        if filter_re.search(entry):
            filtered.append(entry)
    return '\n'.join(filtered)


def render(app_window):
    imgui.begin(
        "console_panel",
        flags=(
            imgui.WindowFlags_.no_collapse
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_title_bar
            | imgui.WindowFlags_.no_bring_to_front_on_focus
        ),
    )
    if imgui.begin_tab_bar("console_tab_bar", imgui.TabBarFlags_.none):
        if imgui.begin_tab_item("Log")[0]:
            log_text = app_window.log_text
            if app_window.log_filter_text != '':
                if (
                    not app_window.log_filter_timestamp
                    or app_window.log_filter_timestamp < app_window.log_text_timestamp
                ):
                    app_window.log_text_filtered = filter_logs(app_window.log_filter_text, log_text)
                    app_window.log_filter_timestamp = datetime.now()
                log_text = app_window.log_text_filtered

            imgui.push_style_var(imgui.StyleVar_.item_spacing, [2, 2])

            imgui.dummy(app_window.scaled(1, 1))
            imgui.begin_group()
            imgui.dummy(app_window.scaled(1, 1))
            imgui.text(" Filter regex:")
            imgui.end_group()
            imgui.same_line()
            imgui.set_next_item_width(200)
            filter_changed, filter_text = imgui.input_text(
                '##log_filter_text', app_window.log_filter_text
            )
            imgui.same_line()
            cur = imgui.get_cursor_pos()
            imgui.set_cursor_pos((
                app_window.window_width - 110*app_window.imgui_global_scale,
                cur[1]
            ))
            _, app_window.log_scroll_follow = imgui.checkbox(
                'Follow log', app_window.log_scroll_follow
            )

            imgui.input_text_multiline(
                'log_output_text',
                log_text,
                (app_window.window_width, app_window.console_panel_height - 2*app_window.menu_height),
                imgui.InputTextFlags_.read_only
            )

            # this is hacky hacky
            # https://github.com/ocornut/imgui/issues/5484
            text_timestamp = app_window.log_text_timestamp
            if (
                app_window.log_scroll_follow
                and text_timestamp
                and (
                    not app_window.log_scroll_timestamp
                    or text_timestamp > app_window.log_scroll_timestamp
                )
            ):
                app_window.log_scroll_timestamp = text_timestamp or datetime.now()
                main_window = imgui.internal.get_current_window()
                child_name = f"{main_window.name}/log_output_text_{imgui.get_id('log_output_text'):08X}"
                child_window = imgui.internal.find_window_by_name(child_name)
                if child_window:
                    imgui.internal.set_scroll_y(
                        child_window,
                        child_window.scroll_max[1]
                    )

            if filter_changed:
                app_window.log_filter_text = filter_text
                app_window.log_filter_timestamp = None
            imgui.pop_style_var()
            imgui.end_tab_item()

        if app_window.console_manager.bring_to_front:
            tabflags = imgui.TabItemFlags_.set_selected
            app_window.console_manager.bring_to_front = False
        else:
            tabflags = 0

        if imgui.begin_tab_item("Console", None, tabflags)[0]:
            if imgui.is_window_hovered(imgui.FocusedFlags_.child_windows):
                app_window.selected_window = "console"
                if not isinstance(app_window.input_mgr.global_mode, ConsoleMode):
                    app_window.input_mgr.global_mode = ConsoleMode(app_window)
                    app_window.input_mgr.major_mode.disable()
                    for m in list(app_window.input_mgr.minor_modes):
                        app_window.input_mgr.disable_minor_mode(m)

            app_window.console_manager.render(
                app_window.window_width,
                app_window.console_panel_height - app_window.menu_height
            )
            imgui.end_tab_item()
        imgui.end_tab_bar()

    imgui.end()
