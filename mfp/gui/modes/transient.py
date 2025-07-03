#! /usr/bin/env/python
'''
transient.py
TransientMessageEditMode -- extend LabelEditMode to allow for dest port
selection

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode
from .label_edit import LabelEditMode


class TransientMessageEditMode (InputMode):
    def __init__(self, window, message, label):
        self.message = message
        self.window = window
        self.label = label

        InputMode.__init__(self, "Send message")

        self.extend(LabelEditMode(window, message, label))

    @classmethod
    def init_bindings(cls):
        cls.bind("transient-C-0", lambda mode: mode.message.set_port(0), "Send to inlet 0", "C-0")
        cls.bind("transient-C-1", lambda mode: mode.message.set_port(1), "Send to inlet 1", "C-1")
        cls.bind("transient-C-2", lambda mode: mode.message.set_port(2), "Send to inlet 2", "C-2")
        cls.bind("transient-C-3", lambda mode: mode.message.set_port(3), "Send to inlet 3", "C-3")
        cls.bind("transient-C-4", lambda mode: mode.message.set_port(4), "Send to inlet 4", "C-4")
        cls.bind("transient-C-5", lambda mode: mode.message.set_port(5), "Send to inlet 5", "C-5")
        cls.bind("transient-C-6", lambda mode: mode.message.set_port(6), "Send to inlet 6", "C-6")
        cls.bind("transient-C-7", lambda mode: mode.message.set_port(7), "Send to inlet 7", "C-7")
        cls.bind("transient-C-8", lambda mode: mode.message.set_port(8), "Send to inlet 8", "C-8")
        cls.bind("transient-C-9", lambda mode: mode.message.set_port(9), "Send to inlet 9", "C-9")
        cls.bind("transient-ESC", lambda mode: mode.cancel(), "Cancel message", "ESC")

        cls.extend_mode(LabelEditMode)

    async def cancel(self):
        await self.message.label_edit_finish(self.label, None)
        return True
