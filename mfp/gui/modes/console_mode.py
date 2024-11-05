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
        cls.bind(
            "console-ret", lambda mode: mode.console.handle_enter(),
            "Evaluate current line", "RET",
        )
        cls.bind(
            "console-up", lambda mode: mode.console.handle_cursor_up(),
            "Cursor up", "UP",
        )
        cls.bind(
            "console-down", lambda mode: mode.console.handle_cursor_down(),
            "Cursor down", "DOWN",
        )
        cls.bind(
            "console-left", lambda mode: mode.console.handle_cursor_left(),
            "Cursor left", "LEFT",
        )
        cls.bind(
            "console-right", lambda mode: mode.console.handle_cursor_right(),
            "Cursor right", "RIGHT",
        )
        cls.bind(
            "console-bs", lambda mode: mode.console.handle_backspace(),
            "Backspace", "BS",
        )
        cls.bind(
            "console-del", lambda mode: mode.console.handle_delete(),
            "Delete", "DEL",
        )
        cls.bind(
            "start-of-line", lambda mode: mode.console.handle_start_of_line(),
            "Move to start of line", "C-a",
        )
        cls.bind(
            "end-of-line", lambda mode: mode.console.handle_end_of_line(),
            "Move to end of line", "C-e",
        )
        cls.bind(
            "delete-to-end", lambda mode: mode.console.handle_delete_to_end(),
            "Delete to end of line", "C-k",
        )

        # catchall -- warning, this gets ALL keysyms, not just text
        cls.bind(
            "default", lambda mode, keysym: mode.console.handle_insert_text(keysym),
            "Insert text", None,
        )
