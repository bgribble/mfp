#! /usr/bin/env python2.6
'''
clickable.py: Control mode for clickable items (message, bang, toggle)

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode
from .label_edit import LabelEditMode

from mfp import log


class ClickableControlMode (InputMode):
    def __init__(self, window, element, descrip):
        self.manager = window.input_mgr
        self.window = window
        self.widget = element
        self.clickstate = False

        InputMode.__init__(self, descrip)

        self.bind("M1DOWN", self.click, "Send click down")
        self.bind("M1DOUBLEDOWN", self.click, "Send click down")
        self.bind("M1TRIPLEDOWN", self.click, "Send click down")

        self.bind("M1UP", self.unclick, "Send click up")
        self.bind("M1DOUBLEUP", self.unclick, "Send click up")
        self.bind("M1TRIPLEUP", self.unclick, "Send click up")

    def enable(self):
        if self.manager.pointer_obj is self.widget:
            self.clickstate = True
            self.widget.clicked()

    def disable(self):
        if self.clickstate:
            self.widget.unclicked()

    def click(self):
        if self.manager.pointer_obj is self.widget:
            self.clickstate = True
            return self.widget.clicked()
        else:
            self.clickstate = False
            self.widget.unclicked()
            return False

    def unclick(self):
        self.clickstate = False
        self.widget.unclicked()
        return False
