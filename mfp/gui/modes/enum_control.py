#! /usr/bin/env python2.6
'''
enum_control.py: EnumControl major mode

Copyright (c) 2010-2013 Bill Gribble <grib@billgribble.com>
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

        self.bind("C->", self.add_digit, "Increase displayed digits")
        self.bind("C-<", self.del_digit, "Decrease displayed digits")
        self.bind("C-[", self.set_lower, "Set lower bound on value")
        self.bind("C-]", self.set_upper, "Set upper bound on value")
        self.extend(LabelEditMode(window, element, label))

    def set_upper(self):
        def cb(value):
            if value.lower() == "none":
                value = None
            else: 
                value = float(value)
            self.enum.set_bounds(self.enum.min_value, value) 
        self.window.get_prompted_input("Number upper bound: ", cb)
        return True 

    def set_lower(self):
        def cb(value):
            if value.lower() == "none":
                value = None
            else: 
                value = float(value)
            self.enum.set_bounds(value, self.enum.max_value) 
        self.window.get_prompted_input("Number lower bound: ", cb)
        return True 

    def add_digit(self):
        self.enum.digits += 1
        self.enum.format_update()
        self.enum.update()
        return True 

    def del_digit(self):
        if self.enum.digits > 0:
            self.enum.digits -= 1
        self.enum.format_update()
        self.enum.update()
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

        self.bind("M1DOWN", self.drag_start)
        self.bind("M1-MOTION", lambda: self.drag_selected(1.0),
                  "Change value (1x speed)")
        self.bind("S-M1-MOTION", lambda: self.drag_selected(10.0),
                  "Change value (10x speed)")
        self.bind("C-M1-MOTION", lambda: self.drag_selected(100.0),
                  "Change value (100x speed)")
        self.bind("M1UP", self.drag_end)
        self.bind("UP", lambda: self.changeval(1.0))
        self.bind("DOWN", lambda: self.changeval(-1.0))

    def changeval(self, delta):
        if self.enum.scientific:
            try:
                logdigits = int(math.log10(self.enum.value))
            except ValueError:
                logdigits = 0

            base_incr = 10 ** (logdigits - self.enum.digits)
        else:
            base_incr = 10 ** (-self.enum.digits)

        self.value = self.enum.value + delta * base_incr
        self.enum.update_value(self.value)
        return True


    def drag_start(self):
        if self.manager.pointer_obj == self.enum:
            if self.manager.pointer_obj not in self.window.selected:
                self.window.select(self.manager.pointer_obj)

            self.drag_started = True
            self.drag_start_x = self.manager.pointer_x
            self.drag_start_y = self.manager.pointer_y
            self.drag_last_x = self.manager.pointer_x
            self.drag_last_y = self.manager.pointer_y
            self.value = self.enum.value
            return True
        else:
            return False

    def drag_selected(self, delta=1.0):
        if self.drag_started is False:
            return False

        dx = self.manager.pointer_x - self.drag_last_x
        dy = self.manager.pointer_y - self.drag_last_y

        self.drag_last_x = self.manager.pointer_x
        self.drag_last_y = self.manager.pointer_y
        self.changeval(-1.0*delta*dy)

        return True

    def drag_end(self):
        if self.drag_started:
            self.drag_started = False
            return True
        else:
            return False
