"""
input handling for imgui window
"""

from datetime import datetime, timedelta
from mfp import log
from mfp.gui import key_defs
from mfp.gui_main import MFPGUI
from ..event import (
    ButtonPressEvent,
    ButtonReleaseEvent,
    KeyPressEvent,
    KeyReleaseEvent,
)
from imgui_bundle import imgui

KEY_REPEAT_DELAY_US = 100000
KEY_REPEAT_INTERVAL_US = 25000
KEY_REPEAT_KEYS = [
    key_defs.KEY_UP,
    key_defs.KEY_DN,
    key_defs.KEY_LEFT,
    key_defs.KEY_RIGHT,
    key_defs.KEY_BKSP,
]


def imgui_key_map():
    """
    Map imgui key ID to mfp key ID
    """

    keymap = {
        imgui.Key.backspace: key_defs.KEY_BKSP,
        imgui.Key.delete: key_defs.KEY_DEL,
        imgui.Key.down_arrow: key_defs.KEY_DN,
        imgui.Key.end: key_defs.KEY_END,
        imgui.Key.enter: key_defs.KEY_ENTER,
        imgui.Key.escape: key_defs.KEY_ESC,
        imgui.Key.home: key_defs.KEY_HOME,
        imgui.Key.mod_ctrl: key_defs.MOD_CTRL,
        imgui.Key.mod_shift: key_defs.MOD_SHIFT,
        imgui.Key.mod_alt: key_defs.MOD_ALT,
        imgui.Key.mod_super: key_defs.MOD_WIN,
        imgui.Key.insert: key_defs.KEY_INS,
        imgui.Key.left_arrow: key_defs.KEY_LEFT,
        imgui.Key.mouse_left: key_defs.MOUSE_LEFT,
        imgui.Key.mouse_middle: key_defs.MOUSE_MIDDLE,
        imgui.Key.mouse_right: key_defs.MOUSE_RIGHT,
        imgui.Key.mouse_wheel_x: key_defs.MOUSE_SCROLL_X,
        imgui.Key.mouse_wheel_y: key_defs.MOUSE_SCROLL_Y,
        imgui.Key.page_down: key_defs.KEY_PGDN,
        imgui.Key.page_up: key_defs.KEY_PGUP,
        imgui.Key.reserved_for_mod_ctrl: key_defs.MOD_CTRL,
        imgui.Key.reserved_for_mod_shift: key_defs.MOD_SHIFT,
        imgui.Key.reserved_for_mod_alt: key_defs.MOD_ALT,
        imgui.Key.right_alt: key_defs.MOD_RALT,
        imgui.Key.right_arrow: key_defs.KEY_RIGHT,
        imgui.Key.right_ctrl: key_defs.MOD_RCTRL,
        imgui.Key.right_shift: key_defs.MOD_RSHIFT,
        imgui.Key.tab: key_defs.KEY_TAB,
        imgui.Key.up_arrow: key_defs.KEY_UP,
    }
    keymap[imgui.Key.space] = ord(' ')

    for index, key in enumerate("0123456789"):
        keymap[imgui.Key(index + 536)] = ord(key)

    for index, key in enumerate("abcdefghijklmnopqrstuvwxyz"):
        keymap[imgui.Key(index + 546)] = ord(key)

    for index, key in enumerate(r"',-./;=[\]`"):
        keymap[imgui.Key(index + 596)] = ord(key)

    # Fn keys
    for index in range(12):
        keymap[imgui.Key(572 + index)] = key_defs.KEY_F1 + index

    return keymap


def keys_down():
    keys = []
    for index in range(512, int(imgui.Key.named_key_end)):
        key = imgui.Key(index)
        key_down = imgui.is_key_down(key)
        if key_down:
            keys.append(key)
    return set(keys)


def imgui_process_inputs(app_window):
    now = datetime.now()
    keys_currently_pressed = keys_down()

    unhandled_windows = ["info", "editor"]

    key_presses = keys_currently_pressed - app_window.keys_pressed
    key_releases = app_window.keys_pressed - keys_currently_pressed

    any_dead_keys = any(
        app_window.keymap.get(k) in key_defs.MOD_DEAD
        for k in keys_currently_pressed
    )

    # make repeat events for cursor keys
    for k in app_window.keys_pressed:
        mfp_key = app_window.keymap.get(k)
        if k not in key_releases and mfp_key in KEY_REPEAT_KEYS:
            next_event = app_window.imgui_repeating_keys.get(mfp_key)
            if next_event and now > next_event:
                key_presses.add(k)

    if key_presses:
        for k in key_presses:
            mfp_key = app_window.keymap.get(k)

            if mfp_key in KEY_REPEAT_KEYS:
                if mfp_key in app_window.imgui_repeating_keys:
                    app_window.imgui_repeating_keys[mfp_key] = (
                        now + timedelta(microseconds=KEY_REPEAT_INTERVAL_US)
                    )
                else:
                    app_window.imgui_repeating_keys[mfp_key] = (
                        now + timedelta(microseconds=KEY_REPEAT_DELAY_US)
                    )

            if mfp_key in key_defs.MOD_ALL or mfp_key in key_defs.KEY_NONPRINT:
                ev = KeyPressEvent(
                    target=app_window.input_mgr.pointer_obj,
                    keyval=mfp_key,
                    unicode=None
                )
                if app_window.selected_window not in unhandled_windows:
                    MFPGUI().async_task(app_window.signal_emit("key-press-event", ev))
            elif mfp_key in key_defs.MOUSE_BUTTONS:
                clickinfo = app_window.mouse_clicks.get(mfp_key)
                click_count = 1
                now = datetime.now()

                if clickinfo and (now - clickinfo[0]).total_seconds() < 0.25:
                    click_count = clickinfo[1] + 1
                app_window.mouse_clicks[mfp_key] = (datetime.now(), click_count)

                ev = ButtonPressEvent(
                    target=app_window.input_mgr.pointer_obj,
                    button=1 + mfp_key - key_defs.MOUSE_LEFT,
                    click_count=click_count
                )
                if app_window.selected_window not in unhandled_windows:
                    MFPGUI().async_task(app_window.signal_emit("button-press-event", ev))
            elif any_dead_keys and mfp_key is not None:
                # this is the case where a mod key is held down and another
                # key is pressed. the sdl2 backend generally doesn't emit
                # SDL_TEXTINPUT for these but does in some cases. We wamt to make
                # sure we don't send double events if there's about to be a
                # SDL_TEXTINPUT right after this.
                need_event = True
                mfp_keys_pressed = [app_window.keymap.get(k) for k in keys_currently_pressed]
                if key_defs.MOD_CTRL in mfp_keys_pressed:
                    txt_keys = [ord(k) for k in "109;,.'"]
                    if mfp_key in txt_keys:
                        need_event = False
                if key_defs.MOD_ALT in mfp_keys_pressed:
                    nontxt_keys = [
                        ord("x"), ord("c"), ord("v"),
                        key_defs.KEY_ENTER, key_defs.KEY_UP, key_defs.KEY_DN,
                        key_defs.KEY_LEFT, key_defs.KEY_RIGHT
                    ]
                    if mfp_key not in nontxt_keys and key_defs.MOD_CTRL not in mfp_keys_pressed:
                        need_event = False

                if need_event:
                    ev = KeyPressEvent(
                        target=app_window.input_mgr.pointer_obj,
                        keyval=mfp_key,
                        unicode=chr(mfp_key)
                    )
                    if app_window.selected_window not in unhandled_windows:
                        MFPGUI().async_task(app_window.signal_emit("key-press-event", ev))

    if key_releases:
        for k in key_releases:
            mfp_key = app_window.keymap.get(k)
            if mfp_key in app_window.imgui_repeating_keys:
                del app_window.imgui_repeating_keys[mfp_key]

            if mfp_key in key_defs.MOD_ALL or mfp_key in key_defs.KEY_NONPRINT:
                ev = KeyReleaseEvent(
                    target=app_window.input_mgr.pointer_obj,
                    keyval=mfp_key,
                    unicode=None
                )
                if app_window.selected_window not in unhandled_windows:
                    MFPGUI().async_task(app_window.signal_emit("key-release-event", ev))
            elif mfp_key in key_defs.MOUSE_BUTTONS:
                clickinfo = app_window.mouse_clicks.get(mfp_key)
                click_count = 1
                if clickinfo:
                    click_count = clickinfo[1]

                ev = ButtonReleaseEvent(
                    target=app_window.input_mgr.pointer_obj,
                    button=1 + mfp_key - key_defs.MOUSE_LEFT,
                    click_count=click_count
                )
                if app_window.selected_window == "canvas":
                    MFPGUI().async_task(app_window.signal_emit("button-release-event", ev))
            elif any_dead_keys and mfp_key is not None:
                ev = KeyReleaseEvent(
                    target=app_window.input_mgr.pointer_obj,
                    keyval=mfp_key,
                    unicode=chr(mfp_key)
                )
                if app_window.selected_window == "canvas":
                    MFPGUI().async_task(app_window.signal_emit("key-release-event", ev))

    app_window.keys_pressed = keys_currently_pressed
