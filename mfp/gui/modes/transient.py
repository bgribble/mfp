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

        self.bind("C-0", lambda: self.message.set_port(0), "Send to inlet 0")
        self.bind("C-1", lambda: self.message.set_port(1), "Send to inlet 1")
        self.bind("C-2", lambda: self.message.set_port(2), "Send to inlet 2")
        self.bind("C-3", lambda: self.message.set_port(3), "Send to inlet 3")
        self.bind("C-4", lambda: self.message.set_port(4), "Send to inlet 4")
        self.bind("C-5", lambda: self.message.set_port(5), "Send to inlet 5")
        self.bind("C-6", lambda: self.message.set_port(6), "Send to inlet 6")
        self.bind("C-7", lambda: self.message.set_port(7), "Send to inlet 7")
        self.bind("C-8", lambda: self.message.set_port(8), "Send to inlet 8")
        self.bind("C-9", lambda: self.message.set_port(9), "Send to inlet 9")
        self.bind("ESC", self.cancel, "Cancel message")

        self.extend(LabelEditMode(window, message, label))

    def cancel(self):
        self.message.label_edit_finish(self.label, None) 
