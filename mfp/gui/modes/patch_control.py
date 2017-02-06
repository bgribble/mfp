#! /usr/bin/env python
'''
patch_control.py: PatchControl major mode

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from ..input_mode import InputMode

class PatchControlMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window

        InputMode.__init__(self, "Operate patch", "Operate")
        
        self.bind("C- ", self.window.edit_major_mode, "Enter edit mode")
        self.bind("TAB", self.select_next, "Select next element")
        self.bind("S-TAB", self.select_prev, "Select previous element")
        self.bind("C-TAB", self.select_mru, "Select most-recent element")

        self.window.add_callback("select", self.begin_control)
        self.window.add_callback("unselect", self.end_control)

    def enable(self):
        self.enabled = True 
        self.manager.global_mode.allow_selection_drag = False 

    def begin_control(self, obj):
        if not self.enabled:
            return False 

        if obj is not None: 
            obj.begin_control()

    def end_control(self, obj):
        if not self.enabled:
            return False 

        if obj is not None:
            obj.end_control()

    def select_next(self):
        self.window.select_next()
        return True

    def select_prev(self):
        self.window.select_prev()
        return True

    def select_mru(self):
        self.window.select_mru()
        return True
