#! /usr/bin/env python
'''
console_mode.py: Global mode when console window is selected

Not used by Clutter backend

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

from mfp.gui_main import MFPGUI
from mfp import log
from ..input_mode import InputMode
from ..input_manager import InputManager


class ConsoleMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.console = window.console_manager
        self.window = window

        InputMode.__init__(self, "Console input bindings")

        # global keybindings
        self.bind("RET", self.console.handle_enter, "Evaluate current line")
        self.bind("UP", self.console.handle_cursor_up, "Cursor up")
        self.bind("DN", self.console.handle_cursor_down, "Cursor down")
        self.bind("LEFT", self.console.handle_cursor_left, "Cursor left")
        self.bind("RIGHT", self.console.handle_cursor_right, "Cursor right")
        self.bind("BS", self.console.handle_backspace, "Backspace")
        self.bind("DEL", self.console.handle_delete, "Delete")
        self.bind("C-a", self.console.handle_start_of_line, "Move to start of line")
        self.bind("C-e", self.console.handle_end_of_line, "Move to end of line")
        self.bind("C-k", self.console.handle_delete_to_end, "Delete to end of line")

        # catchall -- warning, this gets ALL keysyms, not just text
        self.bind(None, self.console.handle_insert_text, "Insert text")
