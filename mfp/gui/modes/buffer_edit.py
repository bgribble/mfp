#! /usr/bin/env python
'''
buffer_edit.py: BufferEdit major mode

Copyright (c) Bill Gribble <grib@billgribble.com>
'''
import numpy as np

from mfp import log
from mfp.gui_main import MFPGUI
from ..input_mode import InputMode


class BufferEditMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window
        self.mouse_down_pos = None

        InputMode.__init__(self, "Edit buffer", "Buffer")

    @property
    def editor(self):
        return self.window.buffer_editor

    @classmethod
    def init_bindings(cls):
        #####################
        # Edit operations
        cls.bind(
            "buffer-edit-cut", cls.cut, helptext="Cut selection to clipboard",
            keysym="C-x", menupath="BufEdit > Cut"
        )
        cls.bind(
            "buffer-edit-copy", cls.copy, helptext="Copy selection to clipboard",
            keysym="C-c", menupath="BufEdit > Copy"
        )
        cls.bind(
            "buffer-edit-paste", cls.paste, helptext="Paste selection from clipboard",
            keysym="C-v", menupath="BufEdit > Paste"
        )
        cls.bind(
            "buffer-edit-paste-stretch", cls.paste_to_fit,
            helptext="Paste from clipboard, stretched to fit selection",
            keysym="C-f", menupath="BufEdit > Paste to fit"
        )
        cls.bind(
            "buffer-edit-clear", cls.clear, helptext="Clear selection",
            keysym="C-k", menupath="BufEdit > Clear"
        )
        cls.bind(
            "buffer-edit-delete", cls.delete, helptext="Delete selection",
            keysym="DEL", menupath="BufEdit > Delete"
        )
        cls.bind(
            "buffer-edit-trim-to-selection", cls.trim, helptext="Trim to selection",
            keysym="DEL", menupath="BufEdit > Trim to selection"
        )
        cls.bind(
            "buffer-edit-insert-silence", cls.insert_silence, helptext="Insert silence at playhead",
            keysym="S", menupath="BufEdit > Insert silence..."
        )

        #####################
        # Select submenu
        cls.bind(
            "buffer-edit-select-all", cls.select_all, helptext="Select all",
            keysym="C-a", menupath="BufEdit > Select > Select all"
        )
        cls.bind(
            "buffer-edit-select-none", cls.select_none, helptext="Unselect all",
            keysym="C-A", menupath="BufEdit > Select > Unselect all"
        )
        cls.bind(
            "buffer-edit-select-silence", cls.select_silence, helptext="Select silence at playhead",
            keysym="s", menupath="BufEdit > Select > Select silence..."
        )

        #####################
        # FX submenu
        cls.bind(
            "buffer-edit-effect-gain", lambda m: m.apply_effect("fx.gain~"),
            helptext="Apply gain effect",
            keysym="g", menupath="BufEdit > Effects > Gain"
        )
        cls.bind(
            "buffer-edit-effect-fadein", lambda m: m.apply_effect("fx.fadein~"),
            helptext="Apply fadein effect",
            keysym="i", menupath="BufEdit > Effects > Fade in"
        )
        cls.bind(
            "buffer-edit-effect-fadeout", lambda m: m.apply_effect("fx.fadeout~"),
            helptext="Apply fadeout effect",
            keysym="o", menupath="BufEdit > Effects > Fade out"
        )
        cls.bind(
            "buffer-edit-effect-complim", lambda m: m.apply_effect("fx.comp~"),
            helptext="Apply compressor/limiter effect",
            keysym="c", menupath="BufEdit > Effects > Comp/limiter"
        )
        cls.bind(
            "buffer-edit-effect-pitch", lambda m: m.apply_effect("fx.pitch~"),
            helptext="Change pitch without time stretch",
            keysym="p", menupath="BufEdit > Effects > Pitch change"
        )
        cls.bind(
            "buffer-edit-effect-3band", lambda m: m.apply_effect("fx.3band~"),
            helptext="3-band EQ",
            keysym="3", menupath="BufEdit > Effects > 3-band EQ"
        )
        cls.bind(
            "buffer-edit-effect-1band", lambda m: m.apply_effect("fx.1band~"),
            helptext="1-band parametric EQ",
            keysym="1", menupath="BufEdit > Effects > 1-band para EQ"
        )

        #####################
        # Transport submenu
        cls.bind(
            "buffer-edit-xport-play", cls.toggle_play, helptext="Play/pause",
            keysym=" ", menupath="BufEdit > Transport > Play/pause"
        )
        cls.bind(
            "buffer-edit-xport-home", cls.playhead_home, helptext="Playhead to start",
            keysym="HOME", menupath="BufEdit > Transport > Playhead to start"
        )
        cls.bind(
            "buffer-edit-xport-end", cls.playhead_end, helptext="Playhead to end",
            keysym="END", menupath="BufEdit > Transport > Playhead to end"
        )
        cls.bind(
            "buffer-edit-xport-loop", cls.playhead_loop_selection, helptext="Loop selection",
            keysym="L", menupath="BufEdit > Transport > Loop selection"
        )

        #####################
        # View submenu
        cls.bind(
            "buffer-edit-view-zoomin", cls.view_zoom_in, helptext="Zoom in",
            keysym="=", menupath="BufEdit > View > Zoom in"
        )
        cls.bind(
            "buffer-edit-view-zoomout", cls.view_zoom_out, helptext="Zoom out",
            keysym="-", menupath="BufEdit > View > Zoom out"
        )
        cls.bind(
            "buffer-edit-view-zoomsel", cls.view_zoom_selection, helptext="Zoom to selection",
            keysym="C-e", menupath="BufEdit > View > Zoom to selection"
        )
        cls.bind(
            "buffer-edit-view-playhead", cls.view_playhead, helptext="Center playhead",
            keysym="C-\\", menupath="BufEdit > View > Center playhead"
        )

        #####################
        # File operations
        cls.bind(
            "buffer-edit-apply", cls.buffer_apply, helptext="Save changes to buffer",
            keysym="C-s", menupath="BufEdit > |Save changes to buffer"
        )
        cls.bind(
            "buffer-edit-import", cls.buffer_import, helptext="Import audio file",
            keysym="C-I", menupath="BufEdit > |Import..."
        )
        cls.bind(
            "buffer-edit-export", cls.buffer_export, helptext="Export audio file",
            keysym="C-E", menupath="BufEdit > |Export..."
        )

        #####################
        # Non-menu keybindins
        cls.bind(
            "buffer-click-down", cls.click_start, helptext="Set playhead position",
            keysym="M1DOWN"
        )
        cls.bind(
            "buffer-click-up", cls.click_end, helptext="Set playhead position",
            keysym="M1UP"
        )
        cls.bind(
            "playhead-backward", lambda mode: mode.playhead_move(-1.0),
            helptext="Move playhead backward",
            keysym="LEFT"
        )
        cls.bind(
            "playhead-backward-fast", lambda mode: mode.playhead_move(-5.0),
            helptext="Move playhead backward quickly",
            keysym="C-LEFT"
        )
        cls.bind(
            "playhead-forward", lambda mode: mode.playhead_move(1.0),
            helptext="Move playhead forward",
            keysym="RIGHT"
        )
        cls.bind(
            "playhead-forward-fast", lambda mode: mode.playhead_move(5.0),
            helptext="Move playhead forward quickly",
            keysym="C-RIGHT"
        )

    def click_start(self, *args):
        from imgui_bundle import imgui
        if self.window.bufedit_menu_open or not self.editor or not self.editor.implot_plot_hovered:
            self.mouse_down_pos = None
            return False

        self.mouse_down_pos = imgui.get_mouse_pos()
        return True


    def click_end(self, *args):
        from imgui_bundle import imgui
        if self.window.bufedit_menu_open or not self.editor or not self.editor.implot_plot_hovered:
            return False

        pos = imgui.get_mouse_pos()
        down = self.mouse_down_pos
        if down and abs(pos[0] - down[0]) < 0.1 and abs(pos[1] - down[1]) < 0.1:
            self.editor.set_playhead_at_pointer()
        self.mouse_down_pos = None
        return True

    async def playhead_move(self, amount):
        # 1x moves 1/1000 of displayed range
        lim = self.editor.implot_limits
        delta_one_x = (lim.x.max - lim.x.min) / 1000.0
        await self.editor.playhead_move(self.editor.implot_playhead + amount * delta_one_x)

    async def buffer_apply(self):
        await self.editor.buffer_apply()
        return True

    async def buffer_import(self, filename=None):
        async def cb(fname):
            if fname:
                await self.editor.buffer_import(fname)
            else:
                self.window.hud_write("Audio file import canceled")

        if filename is None:
            await self.window.cmd_get_input(
                "Audio file to import: ", cb, filename=True
            )
        else:
            await cb(filename)
        return True

    async def buffer_export(self, filename=None):
        async def cb(fname):
            if fname:
                await self.editor.buffer_export(fname)
            else:
                self.window.hud_write("Audio file export canceled")

        if filename is None:
            await self.window.cmd_get_input(
                "File name for export: ", cb, filename=True
            )
        else:
            await cb(filename)
        return True

    async def toggle_play(self):
        if self.editor.implot_playhead_start_time:
            await self.editor.playhead_pause()
        else:
            await self.editor.playhead_start()
        return True

    async def view_zoom_in(self):
        await self.editor.zoom_change(0.25)
        return True

    async def view_zoom_out(self):
        await self.editor.zoom_change(-0.25)
        return True

    async def view_zoom_selection(self):
        await self.editor.zoom_to_selection()
        return True

    async def view_playhead(self):
        await self.editor.playhead_center_view()
        return True

    async def playhead_home(self):
        await self.editor.playhead_move(0)
        return True

    async def playhead_end(self):
        await self.editor.playhead_move(self.editor.implot_total_time - 0.001)
        return True

    async def playhead_loop_selection(self):
        await self.editor.playhead_loop_selection()
        return True

    async def insert_silence(self, duration=None):
        async def cb(dur):
            if dur:
                await self.editor.playhead_insert_data(
                    np.zeros(int(int(dur) * self.editor.buffer_info.rate / 1000))
                )
            else:
                self.window.hud_write("Canceled")

        if duration is None:
            await self.window.cmd_get_input(
                "Silence duration (mS): ", cb, "0"
            )
        else:
            await cb(duration)

    async def select_silence(self, threshold=None):
        async def cb(thresh):
            if thresh:
                await self.editor.playhead_select_silence(float(thresh))
            else:
                self.window.hud_write("Canceled")

        if threshold is None:
            await self.window.cmd_get_input(
                "Silence threshold (dB): ", cb, "-60"
            )
        else:
            await cb(threshold)

    async def select_all(self):
        await self.editor.playhead_set_selection(
            0, self.editor.implot_total_time
        )
        return True

    def select_none(self):
        self.editor.implot_selection = None
        return True

    async def trim(self):
        await self.editor.buffer_trim_to_selection()
        return True

    async def cut(self):
        await self.editor.clipboard_cut()
        return True

    async def copy(self):
        await self.editor.clipboard_copy()
        return True

    async def paste(self):
        await self.editor.clipboard_paste()
        return True

    async def paste_to_fit(self):
        await self.editor.clipboard_paste_to_fit()
        return True

    async def clear(self):
        await self.editor.clipboard_clear()
        return True

    async def delete(self):
        await self.editor.clipboard_delete()
        return True

    async def apply_effect(self, filename):
        await self.editor.fx_open_patch(filename)
        return True

    async def effect_custom(self, filename=None):
        async def cb(fname):
            if fname:
                await self.editor.fx_open_patch(fname)
            else:
                self.window.hud_write("Apply effect canceled")

        if filename is None:
            await self.window.cmd_get_input(
                "Effect patch to load: ", cb,
            )
        else:
            await cb(filename)
        return True
