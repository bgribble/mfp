#! /usr/bin/env python
'''
selection_edit.py: Minor mode with active selection

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode
from .connection import ConnectionMode


class SelectionEditMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window

        InputMode.__init__(self, "Edit selection")

        self.affinity = -10

        self.bind("UP", lambda: self.window.move_selected(0, -1),
                  "Move selection up 1 unit")
        self.bind("DOWN", lambda: self.window.move_selected(0, 1),
                  "Move selection down 1 unit")
        self.bind("LEFT", lambda: self.window.move_selected(-1, 0),
                  "Move selection left one unit")
        self.bind("RIGHT", lambda: self.window.move_selected(1, 0),
                  "Move selection right one unit")

        self.bind("S-UP", lambda: self.window.move_selected(0, -5), "Move selection up 5")
        self.bind("S-DOWN", lambda: self.window.move_selected(0, 5), "Move selection down 5")
        self.bind("S-LEFT", lambda: self.window.move_selected(-5, 0), "Move selection left 5")
        self.bind("S-RIGHT", lambda: self.window.move_selected(5, 0), "Move selection right 5")

        self.bind("C-UP", lambda: self.window.move_selected(0, -25), "Move selection up 25")
        self.bind("C-DOWN", lambda: self.window.move_selected(0, 25), "Move selection down 25")
        self.bind("C-LEFT", lambda: self.window.move_selected(-25, 0), "Move selection left 25")
        self.bind("C-RIGHT", lambda: self.window.move_selected(25, 0), "Move selection right 25")
        self.bind("DEL", self.window.delete_selected, "Delete selection")
        self.bind("BS", self.window.delete_selected, "Delete selection")


class SingleSelectionEditMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window
        InputMode.__init__(self, "Single selection")

        self.affinity = -10

        self.extend(SelectionEditMode(window))

    @classmethod
    def init_bindings(cls):
        cls.cl_bind(
            "connect-from", cls.connect_fwd, "Connect from element", "c",
            menupath="Context > Connect from element"
        )
        cls.cl_bind(
            "connect-to", cls.connect_rev, "Connect to element", "C",
            menupath="Context > Connect to element"
        )
        cls.cl_bind(
            "edit-selected", cls.edit_selected, "Edit element", "RET",
            menupath="Context > Edit element"
        )

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
