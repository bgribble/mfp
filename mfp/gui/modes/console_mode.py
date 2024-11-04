#! /usr/bin/env python
'''
console_mode.py: Global mode when console window is selected

Not used by Clutter backend

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode


class ConsoleMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.console = window.console_manager
        self.window = window

        InputMode.__init__(self, "Console input bindings", "Console")

    @classmethod
    def init_bindings(cls):
        # global keybindings
        cls.cl_bind(
            "console-ret", lambda mode: mode.console.handle_enter(),
            "Evaluate current line", "RET",
        )
        cls.cl_bind(
            "console-up", lambda mode: mode.console.handle_cursor_up(),
            "Cursor up", "UP",
        )
        cls.cl_bind(
            "console-down", lambda mode: mode.console.handle_cursor_down(),
            "Cursor down", "DOWN",
        )
        cls.cl_bind(
            "console-left", lambda mode: mode.console.handle_cursor_left(),
            "Cursor left", "LEFT",
        )
        cls.cl_bind(
            "console-right", lambda mode: mode.console.handle_cursor_right(),
            "Cursor right", "RIGHT",
        )
        cls.cl_bind(
            "console-bs", lambda mode: mode.console.handle_backspace(),
            "Backspace", "BS",
        )
        cls.cl_bind(
            "console-del", lambda mode: mode.console.handle_delete(),
            "Delete", "DEL",
        )
        cls.cl_bind(
            "start-of-line", lambda mode: mode.console.handle_start_of_line(),
            "Move to start of line", "C-a",
        )
        cls.cl_bind(
            "end-of-line", lambda mode: mode.console.handle_end_of_line(),
            "Move to end of line", "C-e",
        )
        cls.cl_bind(
            "delete-to-end", lambda mode: mode.console.handle_delete_to_end(),
            "Delete to end of line", "C-k",
        )

        # catchall -- warning, this gets ALL keysyms, not just text
        cls.cl_bind(
            "default", lambda mode, keysym: mode.console.handle_insert_text(keysym),
            "Insert text", None,
        )
