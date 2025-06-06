#! /usr/bin/env python
'''
enum_control.py: EnumControl major mode

Copyright Bill Gribble <grib@billgribble.com>
'''

import math
from ..input_mode import InputMode
from .label_edit import LabelEditMode


class EnumEditMode (InputMode):
    def __init__(self, window, element, label):
        self.manager = window.input_mgr
        self.window = window
        self.enum = element
        self.value = element.value
        InputMode.__init__(self, "Number box config")
        self.extend(LabelEditMode(window, element, label))

    @classmethod
    def init_bindings(cls):
        cls.bind(
            "enum-add-digit", cls.add_digit, "Increase displayed digits", "C->",
            menupath="Context > ||Params > Increase displayed digits"
        )
        cls.bind(
            "enum-del-digit", cls.del_digit, "Decrease displayed digits", "C-<",
            menupath="Context > ||Params > Decrease displayed digits"
        )
        cls.bind(
            "enum-lower-bound", cls.set_lower, "Set lower bound on value", "C-[",
            menupath="Context > ||Params > Set lower bound"
        )
        cls.bind(
            "enum-upper-bound", cls.set_upper, "Set upper bound on value", "C-]",
            menupath="Context > ||Params > Set upper bound"
        )
        cls.extend_mode(LabelEditMode)

    async def set_upper(self):
        def cb(value):
            if value.lower() == "none":
                value = None
            else:
                value = float(value)
            self.enum.set_bounds(self.enum.min_value, value)
        await self.window.cmd_get_input("Number upper bound: ", cb)
        return True

    async def set_lower(self):
        def cb(value):
            if value.lower() == "none":
                value = None
            else:
                value = float(value)
            self.enum.set_bounds(value, self.enum.max_value)
        await self.window.cmd_get_input("Number lower bound: ", cb)
        return True

    async def add_digit(self):
        self.enum.digits += 1
        self.enum.format_update()
        await self.enum.update()
        return True

    async def del_digit(self):
        if self.enum.digits > 0:
            self.enum.digits -= 1
        self.enum.format_update()
        await self.enum.update()
        return True

    def end_edits(self):
        self.manager.disable_minor_mode(self)
        self.enum.edit_mode = None
        return False


class EnumControlMode (InputMode):
    def __init__(self, window, element):
        self.manager = window.input_mgr
        self.window = window
        self.enum = element
        self.value = element.value

        self.drag_started = False
        self.drag_start_x = self.manager.pointer_x
        self.drag_start_y = self.manager.pointer_y
        self.drag_last_x = self.manager.pointer_x
        self.drag_last_y = self.manager.pointer_y

        InputMode.__init__(self, "Number box control")

    @classmethod
    def init_bindings(cls):
        cls.bind(
            "enum-drag-start", cls.drag_start, "Start number control", "M1DOWN",
        )
        cls.bind(
            "enum-drag-start-10x", cls.drag_start, "Start number control", "S-M1DOWN",
        )
        cls.bind(
            "enum-drag-start-100x", cls.drag_start, "Start number control", "C-M1DOWN",
        )
        cls.bind(
            "enum-drag-motion", lambda mode: mode.drag_selected(1.0),
            "Change value (1x speed)", "M1-MOTION",
        )
        cls.bind(
            "enum-drag-motion-10x", lambda mode: mode.drag_selected(10.0),
            "Change value (10x speed)", "S-M1-MOTION",
        )
        cls.bind(
            "enum-drag-motion-100x", lambda mode: mode.drag_selected(100.0),
            "Change value (100x speed)", "C-M1-MOTION",
        )
        cls.bind(
            "enum-drag-end", cls.drag_end, "End number control", "M1UP",
        )
        cls.bind(
            "enum-drag-end-10x", cls.drag_end, "End number control", "S-M1UP",
        )
        cls.bind(
            "enum-drag-end-100x", cls.drag_end, "End number control", "C-M1UP",
        )
        cls.bind(
            "enum-val-up", lambda mode: mode.changeval(1.0), "Increase value", "UP",
        )
        cls.bind(
            "enum-val-down", lambda mode: mode.changeval(-1.0), "Decrease value", "DOWN",
        )

    async def changeval(self, delta):
        if self.enum.scientific:
            try:
                logdigits = int(math.log10(self.enum.value))
            except ValueError:
                logdigits = 0

            base_incr = 10 ** (logdigits - self.enum.digits)
        else:
            base_incr = 10 ** (-self.enum.digits)

        self.value = self.enum.value + delta * base_incr
        await self.enum.update_value(self.value)
        return True

    async def drag_start(self):
        if self.manager.pointer_obj == self.enum:
            if self.manager.pointer_obj not in self.window.selected:
                await self.window.select(self.manager.pointer_obj)

            self.drag_started = True
            self.drag_start_x = self.manager.pointer_x
            self.drag_start_y = self.manager.pointer_y
            self.drag_last_x = self.manager.pointer_x
            self.drag_last_y = self.manager.pointer_y
            self.value = self.enum.value
            return True
        return False

    async def drag_selected(self, delta=1.0):
        if self.drag_started is False:
            return False

        dy = self.manager.pointer_y - self.drag_last_y

        self.drag_last_x = self.manager.pointer_x
        self.drag_last_y = self.manager.pointer_y
        await self.changeval(-1.0*delta*dy)

        return True

    def drag_end(self):
        if self.drag_started:
            self.drag_started = False
            return True
        return False
