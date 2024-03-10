"""
input handling for imgui window
"""

from mfp import log
from mfp.gui import key_defs
from mfp.gui_main import MFPGUI
from ..event import (
    KeyPressEvent,
    KeyReleaseEvent,
)
import imgui


def imgui_key_map():
    """
    Map imgui key ID to mfp key ID
    """
    keymap = {
        imgui.get_key_index(imgui.KEY_BACKSPACE): key_defs.KEY_BKSP,
        imgui.get_key_index(imgui.KEY_DELETE): key_defs.KEY_DEL,
        imgui.get_key_index(imgui.KEY_DOWN_ARROW): key_defs.KEY_DN,
        imgui.get_key_index(imgui.KEY_END): key_defs.KEY_END,
        imgui.get_key_index(imgui.KEY_ENTER): key_defs.KEY_ENTER,
        imgui.get_key_index(imgui.KEY_ESCAPE): key_defs.KEY_ESC,
        imgui.get_key_index(imgui.KEY_HOME): key_defs.KEY_HOME,
        imgui.get_key_index(imgui.KEY_INSERT): key_defs.KEY_INS,
        imgui.get_key_index(imgui.KEY_LEFT_ARROW): key_defs.KEY_LEFT,
        imgui.get_key_index(imgui.KEY_MOD_ALT): key_defs.MOD_ALT,
        imgui.get_key_index(imgui.KEY_MOD_SUPER): key_defs.MOD_WIN,
        imgui.get_key_index(imgui.KEY_PAGE_DOWN): key_defs.KEY_PGDN,
        imgui.get_key_index(imgui.KEY_PAGE_UP): key_defs.KEY_PGUP,
        imgui.get_key_index(imgui.KEY_RIGHT_ARROW): key_defs.KEY_RIGHT,
        imgui.get_key_index(imgui.KEY_TAB): key_defs.KEY_TAB,
        imgui.get_key_index(imgui.KEY_UP_ARROW): key_defs.KEY_UP,
    }

    # other mod keys not in imgui special list
    keymap[229] = key_defs.MOD_RSHIFT
    keymap[225] = key_defs.MOD_SHIFT
    keymap[226] = key_defs.MOD_ALT
    keymap[230] = key_defs.MOD_RALT
    keymap[57] = key_defs.MOD_CTRL
    keymap[228] = key_defs.MOD_RCTRL

    # 4-39
    for index, key in enumerate("abcdefghijklmnopqrstuvwxyz1234567890"):
        keymap[index + 4] = ord(key)

    # 44-56 (50, 53 are mystery keys)
    for index, key in enumerate(r" -=[]\ ;' ,./"):
        keymap[index + 44] = ord(key)

    # Fn keys
    for index in range(12):
        keymap[58 + index] = key_defs.KEY_F1 + index

    return keymap


def keys_down():
    keys = []
    index = 0
    while True:
        try:
            key_down = imgui.is_key_down(index)
            if key_down:
                keys.append(index)
            index += 1
        except Exception:
            break
    return set(keys)


def imgui_process_inputs(app_window):
    keys_currently_pressed = keys_down()

    key_presses = keys_currently_pressed - app_window.keys_pressed
    key_releases = app_window.keys_pressed - keys_currently_pressed

    any_dead_keys = any(
        app_window.keymap.get(k) in key_defs.MOD_DEAD
        for k in keys_currently_pressed
    )

    if key_presses:
        for k in key_presses:
            mfp_key = app_window.keymap.get(k)
            if mfp_key in key_defs.MOD_ALL or mfp_key in key_defs.KEY_NONPRINT:
                ev = KeyPressEvent(
                    target=app_window.input_mgr.pointer_obj,
                    keyval=mfp_key,
                    unicode=None
                )
                MFPGUI().async_task(app_window.signal_emit("key-press-event", ev))
            elif any_dead_keys:
                ev = KeyPressEvent(
                    target=app_window.input_mgr.pointer_obj,
                    keyval=mfp_key,
                    unicode=chr(mfp_key)
                )
                MFPGUI().async_task(app_window.signal_emit("key-press-event", ev))

    if key_releases:
        for k in key_releases:
            mfp_key = app_window.keymap.get(k)
            if mfp_key:
                ev = KeyReleaseEvent(
                    target=app_window.input_mgr.pointer_obj,
                    keyval=mfp_key,
                    unicode=None
                )
                MFPGUI().async_task(app_window.signal_emit("key-release-event", ev))

    app_window.keys_pressed = keys_currently_pressed
