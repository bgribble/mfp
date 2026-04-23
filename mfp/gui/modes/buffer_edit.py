#! /usr/bin/env python
'''
buffer_edit.py: BufferEdit major mode

Copyright (c) Bill Gribble <grib@billgribble.com>
'''
from mfp import log
from mfp.gui_main import MFPGUI
from ..input_mode import InputMode


class BufferEditMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window
        self.editor = window.buffer_editor
        self.mouse_down_pos = None

        InputMode.__init__(self, "Edit buffer", "Buffer")

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
            "buffer-edit-clear", cls.clear, helptext="Clear selection",
            keysym="C-k", menupath="BufEdit > Clear"
        )
        cls.bind(
            "buffer-edit-delete", cls.delete, helptext="Delete selection",
            keysym="DEL", menupath="BufEdit > Delete"
        )

        #####################
        # Select submenu
        cls.bind(
            "buffer-edit-select-all", cls.select_all, helptext="Select all",
            keysym="C-a", menupath="BufEdit > Select > Select all"
        )
        cls.bind(
            "buffer-edit-select-none", cls.select_none, helptext="Clear selection",
            keysym="C-A", menupath="BufEdit > Select > Clear selection"
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
            "buffer-edit-custom-effect", cls.effect_custom, helptext="Apply custom effect",
            keysym="f", menupath="BufEdit > Effects > |Custom"
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
        # Non-menu keybindins
        cls.bind(
            "buffer-click-down", cls.click_start, helptext="Set playhead position",
            keysym="M1DOWN"
        )
        cls.bind(
            "buffer-click-up", cls.click_end, helptext="Set playhead position",
            keysym="M1UP"
        )

    def click_start(self, *args):
        from imgui_bundle import imgui
        self.mouse_down_pos = imgui.get_mouse_pos()

    def click_end(self, *args):
        from imgui_bundle import imgui
        pos = imgui.get_mouse_pos()
        down = self.mouse_down_pos
        if down and abs(pos[0] - down[0]) < 0.1 and abs(pos[1] - down[1]) < 0.1:
            self.editor.set_playhead_at_pointer()
        self.mouse_down_pos = None

    async def toggle_play(self):
        if self.editor.implot_playhead_start_time:
            await self.editor.playhead_pause()
        else:
            await self.editor.playhead_start()

    async def view_zoom_in(self):
        await self.editor.zoom_change(0.25)

    async def view_zoom_out(self):
        await self.editor.zoom_change(-0.25)

    async def view_zoom_selection(self):
        await self.editor.zoom_to_selection()

    async def view_playhead(self):
        await self.editor.playhead_center_view()

    async def playhead_home(self):
        await self.editor.playhead_move(0)

    async def playhead_end(self):
        await self.editor.playhead_move(self.editor.implot_total_time - 0.001)

    async def playhead_loop_selection(self):
        await self.editor.playhead_loop_selection()

    async def select_all(self):
        await self.editor.playhead_set_selection(
            0, self.editor.implot_total_time
        )

    def select_none(self):
        self.editor.implot_selection = None

    async def cut(self):
        await self.editor.clipboard_cut()

    async def copy(self):
        await self.editor.clipboard_copy()

    async def paste(self):
        await self.editor.clipboard_paste()

    async def clear(self):
        await self.editor.clipboard_clear()

    async def delete(self):
        await self.editor.clipboard_delete()

    async def apply_effect(self, filename):
        await self.editor.fx_open_patch(filename)

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
