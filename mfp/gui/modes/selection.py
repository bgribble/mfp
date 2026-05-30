#! /usr/bin/env python
'''
selection.py: Minor mode with active selection

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

from mfp import log
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

        self.resize_start_x = None
        self.resize_start_y = None
        self.resize_start_w = None
        self.resize_start_h = None
        self.resize_target = None

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
        cls.bind(
            "resize-start", cls.resize_start, helptext="Start element resize box",
            keysym="M1DOWN"
        )
        cls.bind(
            "resize-motion", cls.resize_motion, helptext="Drag to resize",
            keysym="M1-MOTION"
        )
        cls.bind(
            "resize-end", cls.resize_end, helptext="End resize",
            keysym="M1UP"
        )
        cls.extend_mode(SelectionEditMode)

    def edit_selected(self):
        from mfp.gui_main import MFPGUI
        if self.window.selected:
            MFPGUI().async_task(self.window.selected[0].begin_edit())
            return True
        return False

    def resize_start(self):
        if not self.window.selected:
            return False

        # is pointer in resize grabber?
        if not self.window.selected[0].edit_mode:
            return False

        self.resize_target = self.window.selected[0]
        self.resize_start_x = self.window.input_mgr.pointer_x
        self.resize_start_y = self.window.input_mgr.pointer_y
        self.resize_start_w = max(self.resize_target.min_width, self.resize_target.width)
        self.resize_start_h = max(self.resize_target.min_height, self.resize_target.height)
        return True

    def resize_motion(self):
        from mfp.gui_main import MFPGUI

        if (
            not self.resize_target
            or not self.window.selected
            or self.window.selected[0] != self.resize_target
        ):
            self.resize_target = None
            return False

        dx = self.window.input_mgr.pointer_x - self.resize_start_x
        dy = self.window.input_mgr.pointer_y - self.resize_start_y
        MFPGUI().async_task(self.resize_drag(dx, dy))
        return True

    def resize_end(self):
        if self.resize_target:
            self.resize_target = None
            return True
        return False

    async def resize_drag(self, dw, dh):
        await self.resize_target.dispatch(
            self.resize_target.action(
                self.resize_target.SET_MIN_WIDTH,
                value=self.resize_start_w + dw,
            ),
        )
        await self.resize_target.dispatch(
            self.resize_target.action(
                self.resize_target.SET_MIN_HEIGHT,
                value=self.resize_start_h + dh,
            ),
        )

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
