#! /usr/bin/env python
'''
patch_control.py: PatchControl major mode

Copyright (c) Bill Gribble <grib@billgribble.com>
'''
from ..input_mode import InputMode


class PatchControlMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window

        InputMode.__init__(self, "Operate patch", "Operate")

        self.bind("C- ", self.window.edit_major_mode, "Enter edit mode")
        self.bind("TAB", self.select_next, "Select next element")
        self.bind("S-TAB", self.select_prev, "Select previous element")
        self.bind("C-TAB", self.select_mru, "Select most-recent element")

        self.window.signal_listen("select", self.begin_control)
        self.window.signal_listen("unselect", self.end_control)

    def enable(self):
        self.enabled = True
        self.manager.global_mode.allow_selection_drag = False

    def begin_control(self, window, signal, obj):
        if not self.enabled:
            return False

        if obj is not None:
            obj.begin_control()

    def end_control(self, window, signal, obj):
        if not self.enabled:
            return False

        if obj is not None:
            obj.end_control()

    async def select_next(self):
        await self.window.select_next()
        return True

    async def select_prev(self):
        await self.window.select_prev()
        return True

    async def select_mru(self):
        await self.window.select_mru()
        return True
