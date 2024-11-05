#! /usr/bin/env python
'''
clickable.py: Control mode for clickable items (message, bang, toggle)

Copyright (c) Bill Gribble <grib@billgribble.com>
'''
from ..input_manager import InputManager
from ..input_mode import InputMode
from .label_edit import LabelEditMode

from mfp import log


class ClickableControlMode (InputMode):
    MOD_PREFIX = ''

    def __init__(self, window, element, descrip):
        self.manager = window.input_mgr
        self.window = window
        self.widget = element
        self.clickstate = False

        InputMode.__init__(self, descrip)

    @classmethod
    def init_bindings(cls):
        cls.bind("clickable-down", cls.click, "Send click down", cls.MOD_PREFIX + "M1DOWN", )
        cls.bind("clickable-doubledown", cls.click, "Send click down", cls.MOD_PREFIX + "M1DOUBLEDOWN", )
        cls.bind("clickable-tripledown", cls.click, "Send click down", cls.MOD_PREFIX + "M1TRIPLEDOWN", )

        cls.bind("clickable-up", cls.unclick, "Send click up", cls.MOD_PREFIX + "M1UP", )
        cls.bind("clickable-doubleup", cls.unclick, "Send click up",  cls.MOD_PREFIX + "M1DOUBLEUP", )
        cls.bind("clickable-tripleup", cls.unclick, "Send click up", cls.MOD_PREFIX + "M1TRIPLEUP", )

        cls.bind(
            "clickable-ret", cls.quick_click, "Send click", "RET",
            menupath="Context > Send click"
        )

    def disable(self):
        if self.clickstate:
            self.widget.unclicked()

    def click(self):
        if self.manager.pointer_obj is self.widget:
            self.clickstate = True
            return self.widget.clicked()
        self.clickstate = False
        self.widget.unclicked()
        return False

    def unclick(self):
        self.clickstate = False
        self.widget.unclicked()
        return False

    async def quick_click(self):
        self.clickstate = True
        await self.widget.clicked()
        self.clickstate = False
        self.widget.unclicked()
        return True


class AltClickableControlMode (ClickableControlMode):
    MOD_PREFIX = 'A-'
