"""
buffer_editor/menu_button.py -- hamburger menu in buffer editor

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

import re
from mfp import log
from imgui_bundle import imgui
from ..app_window.menu_bar import add_menu_items, load_menupaths


def render_bufedit_menu(app_window):
    from mfp.gui_main import MFPGUI
    quit_selected = False

    by_menu = load_menupaths(app_window)

    imgui.push_style_var(imgui.StyleVar_.window_padding, (8, 8))
    imgui.push_style_var(imgui.StyleVar_.item_spacing, (0, 3))
    if imgui.begin_popup("##bufedit_popup"):
        imgui.begin_group()

        add_menu_items(app_window, by_menu.get("BufEdit", {}))

        if app_window.buffer_info is None:
            MFPGUI().async_task(app_window.update_buffer_info())
            app_window.buffer_info = []

        if app_window.buffer_selected is None and len(app_window.buffer_info):
            app_window.buffer_selected = app_window.buffer_info[0]

        imgui.dummy(app_window.scaled(1, 2))
        imgui.separator()
        imgui.dummy(app_window.scaled(1, 2))

        for ind, buffer_info in enumerate(app_window.buffer_info):
            if buffer_info.get('proc_name') in ("source_buffer", "sink_buffer"):
                continue

            imgui.push_id(str(id(buffer_info)))
            imgui.dummy(app_window.scaled(1, 1))
            imgui.same_line()
            display_name = f"{buffer_info.get('proc_name')} ({buffer_info.get('buf_info').file_name or 'No file'})"
            buffer_selected, _ = imgui.menu_item(
                display_name,
                '',
                app_window.buffer_selected == buffer_info
            )
            if buffer_selected:
                app_window.buffer_selected = buffer_info
                app_window.buffer_editor.buffer_source_info = buffer_info
                app_window.buffer_editor.buffer_info = buffer_info.get('buf_info')
                # update data in chart
                app_window.buffer_editor.shm_obj = None
                app_window.buffer_editor.buffer_grab()
                MFPGUI().async_task(app_window.buffer_editor.init_working_patch())
            imgui.pop_id()

        imgui.end_group()
        content_size = imgui.get_item_rect_size()
        imgui.set_window_pos((
           app_window.window_width - content_size[0] - 32,
           app_window.window_height - app_window.console_panel_height
        ))

        imgui.end_popup()
        imgui.pop_style_var(2)
    else:
        imgui.pop_style_var(2)
    return quit_selected


