#! /usr/bin/env python
'''
selection.py: Minor mode with active selection

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode
from .connection import ConnectionMode


class SelectionEditMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window

        InputMode.__init__(self, "Edit selection")

        self.affinity = -10

    @classmethod
    def init_bindings(cls):
        cls.bind("selection-UP", lambda mode: mode.window.move_selected(0, -1), "Move selection up 1 unit", "UP", )
        cls.bind("selection-DOWN", lambda mode: mode.window.move_selected(0, 1), "Move selection down 1 unit", "DOWN", )
        cls.bind("selection-LEFT", lambda mode: mode.window.move_selected(-1, 0), "Move selection left one unit", "LEFT", )
        cls.bind("selection-RIGHT", lambda mode: mode.window.move_selected(1, 0), "Move selection right one unit", "RIGHT", )

        cls.bind("selection-S-UP", lambda mode: mode.window.move_selected(0, -5), "Move selection up 5", "S-UP", )
        cls.bind("selection-S-DOWN", lambda mode: mode.window.move_selected(0, 5), "Move selection down 5", "S-DOWN", )
        cls.bind("selection-S-LEFT", lambda mode: mode.window.move_selected(-5, 0), "Move selection left 5", "S-LEFT", )
        cls.bind("selection-S-RIGHT", lambda mode: mode.window.move_selected(5, 0), "Move selection right 5", "S-RIGHT", )

        cls.bind("selection-C-UP", lambda mode: mode.window.move_selected(0, -25), "Move selection up 25", "C-UP", )
        cls.bind("selection-C-DOWN", lambda mode: mode.window.move_selected(0, 25), "Move selection down 25", "C-DOWN", )
        cls.bind("selection-C-LEFT", lambda mode: mode.window.move_selected(-25, 0), "Move selection left 25", "C-LEFT", )
        cls.bind("selection-C-RIGHT", lambda mode: mode.window.move_selected(25, 0), "Move selection right 25", "C-RIGHT", )
        cls.bind("selection-DEL", lambda mode: mode.window.delete_selected(), "Delete selection", "DEL", )
        cls.bind("selection-BS", lambda mode: mode.window.delete_selected(), "Delete selection", "BS", )


class SingleSelectionEditMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window
        InputMode.__init__(self, "Single selection")

        self.affinity = -10

        self.extend(SelectionEditMode(window))

    @classmethod
    def init_bindings(cls):
        cls.bind(
            "edit-selected", cls.edit_selected, "Edit element", "RET",
            menupath="Context > Edit element"
        )
        cls.bind(
            "connect-from", cls.connect_fwd, "Connect from element", "c",
            menupath="Context > |Connect from element"
        )
        cls.bind(
            "connect-to", cls.connect_rev, "Connect to element", "C",
            menupath="Context > |Connect to element"
        )
        cls.extend_mode(SelectionEditMode)

    async def edit_selected(self):
        await self.window.selected[0].begin_edit()

    def connect_fwd(self):
        if self.window.selected:
            for s in self.window.selected:
                if s.editable:
                    self.manager.enable_minor_mode(ConnectionMode(self.window, s))
                    return True
        return False

    def connect_rev(self):
        if self.window.selected:
            for s in self.window.selected:
                if s.editable:
                    self.manager.enable_minor_mode(ConnectionMode(self.window, s, connect_rev=True))
                    return True
        return False


class MultiSelectionEditMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window
        InputMode.__init__(self, "Multiple selection")

        self.affinity = -10

        self.extend(SelectionEditMode(window))

    @classmethod
    def init_bindings(cls):
        cls.extend_mode(SelectionEditMode)
