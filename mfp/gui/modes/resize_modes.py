#! /usr/bin/env python
'''
resize_modes.py: Helper minor modes for dragging around dock panes

Copyright (c) Bill Gribble <grib@billgribble.com>
'''
from mfp import log
from mfp.gui_main import MFPGUI
from ..input_mode import InputMode


class ConsoleResizeMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window
        self.pointer_x = None
        self.pointer_y = None
        self.console_panel_height = None
        InputMode.__init__(self, "Console resize", "Resize")

    @classmethod
    def init_bindings(cls):
        #####################
        # only thing that registers in this mode is dragging
        cls.bind(
            "console-resize-start", lambda mode: mode.resize_start(), helptext="Start resize",
            keysym="M1DOWN"
        )

        cls.bind(
            "console-resize-motion", lambda mode: mode.resize_motion(), helptext="Drag resize handle",
            keysym="M1-MOTION"
        )

        cls.bind(
            "console-resize-finish", lambda mode: mode.resize_finish(), helptext="Finish resize",
            keysym="M1UP"
        )

    def resize_start(self):
        self.pointer_x = self.manager.pointer_ev_x
        self.pointer_y = self.manager.pointer_ev_y
        self.console_panel_height = self.window.console_panel_height
        self.window.canvas_resize_in_progress = True
        return True

    def resize_motion(self):
        px = self.manager.pointer_ev_x - self.pointer_x
        py = self.manager.pointer_ev_y - self.pointer_y
        self.window.console_panel_height = self.console_panel_height - py
        self.window.console_panel_height_set = True
        return True

    def resize_finish(self):
        self.window.canvas_resize_in_progress = False
        return True

    def disable(self):
        self.window.canvas_resize_in_progress = False
        return super().disable()

class InfoResizeMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window
        self.pointer_x = None
        self.pointer_y = None
        self.info_panel_width = None
        InputMode.__init__(self, "Info panel resize", "Resize")

    @classmethod
    def init_bindings(cls):
        #####################
        # only thing that registers in this mode is dragging
        cls.bind(
            "info-resize-start", lambda mode: mode.resize_start(), helptext="Start resize",
            keysym="M1DOWN"
        )

        cls.bind(
            "info-resize-motion", lambda mode: mode.resize_motion(), helptext="Drag resize handle",
            keysym="M1-MOTION"
        )
        cls.bind(
            "info-resize-finish", lambda mode: mode.resize_finish(), helptext="Finish resize",
            keysym="M1UP"
        )

    def resize_start(self):
        self.pointer_x = self.manager.pointer_ev_x
        self.pointer_y = self.manager.pointer_ev_y
        self.info_panel_width = self.window.info_panel_width
        self.window.canvas_resize_in_progress = True
        return True

    def resize_motion(self):
        px = self.manager.pointer_ev_x - self.pointer_x
        py = self.manager.pointer_ev_y - self.pointer_y
        self.window.info_panel_width = self.info_panel_width - px
        self.window.info_panel_width_set = True
        return True

    def resize_finish(self):
        self.window.canvas_resize_in_progress = False
        return True

    def disable(self):
        self.window.canvas_resize_in_progress = False
        return super().disable()
