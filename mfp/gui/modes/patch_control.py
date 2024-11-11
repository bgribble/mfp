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

        super().__init__("Operate patch", "Operate")

        self.window.signal_listen("select", self.begin_control)
        self.window.signal_listen("unselect", self.end_control)

    @classmethod
    def init_bindings(cls):
        cls.bind(
            "select-next", cls.select_next, helptext="Select next element",
            keysym="TAB", menupath="Edit > |Select next"
        )
        cls.bind(
            "select-previous", cls.select_prev, helptext="Select previous element",
            keysym="S-TAB", menupath="Edit > |Select previous"
        )
        cls.bind(
            "select-recent", cls.select_mru, helptext="Select most-recent element",
            keysym="C-TAB", menupath="Edit > |Select recent"
        )
        cls.bind(
            "edit-mode", cls.edit_mode, helptext="Enter edit mode",
            keysym="C- ", menupath="Edit > ||Edit mode"
        )

    def enable(self):
        self.enabled = True
        self.manager.global_mode.allow_selection_drag = False

    def begin_control(self, window, signal, obj):
        if not self.enabled:
            return False

        if obj is not None:
            return obj.begin_control()

        return False

    def end_control(self, window, signal, obj):
        if not self.enabled:
            return False

        if obj is not None:
            obj.end_control()

    def edit_mode(self):
        return self.window.edit_major_mode()

    async def select_next(self):
        await self.window.select_next()
        return True

    async def select_prev(self):
        await self.window.select_prev()
        return True

    async def select_mru(self):
        await self.window.select_mru()
        return True
