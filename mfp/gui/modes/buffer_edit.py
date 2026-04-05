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
            "buffer-edit-custom-effect", cls.effect_custom, helptext="Apply custom effect",
            keysym="f", menupath="BufEdit > Effect"
        )

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

    def cut(self):
        log.debug("[bufedit] cut")

    def copy(self):
        log.debug("[bufedit] copy")

    def paste(self):
        log.debug("[bufedit] paste")

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
