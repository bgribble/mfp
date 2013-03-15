#! /usr/bin/env python
'''
selection_edit.py: Minor mode with active selection

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode
from .connection import ConnectionMode
from ..message_element import TransientMessageElement

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
        self.bind("!", self.transient_msg, "Send message to selection")
        self.bind("DEL", self.window.delete_selected, "Delete selection")
        self.bind("BS", self.window.delete_selected, "Delete selection")

    def transient_msg(self):
        if self.window.selected is not None:
            return self.window.add_element(TransientMessageElement)
        else:
            return False

class SingleSelectionEditMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window
        InputMode.__init__(self, "Single selection")

        self.affinity = -10 

        self.bind("c", self.connect_fwd, "Connect from element")
        self.bind("C", self.connect_rev, "Connect to element")
        self.bind("RET", self.edit_selected, "Edit element")
        self.extend(SelectionEditMode(window))

    def edit_selected(self):
        self.window.selected[0].begin_edit() 

    def connect_fwd(self):
        if self.window.selected:
            self.manager.enable_minor_mode(ConnectionMode(self.window, self.window.selected))
        return True

    def connect_rev(self):
        if self.window.selected:
            self.manager.enable_minor_mode(ConnectionMode(self.window, self.window.selected,
                                                          connect_rev=True))
        return True

class MultiSelectionEditMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window
        InputMode.__init__(self, "Multiple selection")

        self.affinity = -10

        self.extend(SelectionEditMode(window))

    def connect_fwd(self):
        if self.window.selected:
            self.manager.enable_minor_mode(ConnectionMode(self.window, self.window.selected))
        return True

    def connect_rev(self):
        if self.window.selected:
            self.manager.enable_minor_mode(ConnectionMode(self.window, self.window.selected,
                                                          connect_rev=True))
        return True


