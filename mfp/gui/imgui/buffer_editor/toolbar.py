"""
Toolbar render method for buffer editor
"""

from datetime import datetime
from imgui_bundle import imgui

from mfp import log
from mfp.utils import extends
from mfp.gui import image_utils
from mfp.gui.colordb import ColorDB
from .buffer_editor import BufferEditor


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


@extends(BufferEditor)
def render_toolbar(self):
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
        imgui.Col_.button, ColorDB().find('default-button-color').to_rgbaf()
    )
    imgui.push_style_color(
        imgui.Col_.button_hovered, ColorDB().find('default-button-color-highlight').to_rgbaf()
    )
    imgui.push_style_color(
        imgui.Col_.button_active, ColorDB().find('default-button-color-clicked').to_rgbaf()
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
            imgui.Col_.button, ColorDB().find('play-button-color').to_rgbaf()
        )
        imgui.push_style_color(
            imgui.Col_.button_hovered, ColorDB().find('play-button-color-highlight').to_rgbaf()
        )
        imgui.push_style_color(
            imgui.Col_.button_active, ColorDB().find('play-button-color-clicked').to_rgbaf()
        )
    if imgui.image_button(
        "##play_btn", imgui.ImTextureRef(play_tex[0]), [button_size, button_size]
    ):
        MFPGUI().async_task(self.playhead_start())
    if self.implot_playhead_start_time:
        imgui.pop_style_color(3)

    imgui.same_line()

    if imgui.image_button(
        "##stop_btn", imgui.ImTextureRef(stop_tex[0]), [button_size, button_size]
    ):
        MFPGUI().async_task(self.playhead_pause(0))
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

    now = datetime.now()
    toggle = int(now.timestamp()*2) % 2
    if self.rec_enabled:
        if self.rec_recording:
            imgui.push_style_color(
                imgui.Col_.button, ColorDB().find('rec-button-color').to_rgbaf()
            )
            imgui.push_style_color(
                imgui.Col_.button_hovered, ColorDB().find('rec-button-color-highlight').to_rgbaf()
            )
        elif toggle:
            imgui.push_style_color(
                imgui.Col_.button, ColorDB().find('rec-button-color').to_rgbaf()
            )
            imgui.push_style_color(
                imgui.Col_.button_hovered, ColorDB().find('rec-button-color-highlight').to_rgbaf()
            )
    imgui.push_style_color(
        imgui.Col_.button_active, ColorDB().find('rec-button-color-clicked').to_rgbaf()
    )
    if imgui.image_button(
        "##record_btn", imgui.ImTextureRef(record_tex[0]), [button_size, button_size]
    ):
        MFPGUI().async_task(self.playhead_toggle_record())

    imgui.pop_style_color()
    if self.rec_enabled and (self.rec_recording or toggle):
        imgui.pop_style_color(2)
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
