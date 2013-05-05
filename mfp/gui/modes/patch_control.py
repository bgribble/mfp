#! /usr/bin/env python2.6
'''
patch_control.py: PatchControl major mode

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from ..input_mode import InputMode
from mfp.main import MFPApp


class PatchControlMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window

        self.drag_started = True
        self.drag_start_x = self.manager.pointer_x
        self.drag_start_y = self.manager.pointer_y
        self.drag_last_x = self.manager.pointer_x
        self.drag_last_y = self.manager.pointer_y

        InputMode.__init__(self, "Operate patch", "Operate")
        
        self.bind("C- ", self.window.edit_major_mode, "Enter edit mode")
        self.bind("TAB", self.window.select_next, "Select next element")
        self.bind("S-TAB", self.window.select_prev, "Select previous element")
        self.bind("C-TAB", self.window.select_mru, "Select most-recent element")

        self.bind("M1DOWN", self.drag_start)
        self.bind("M1-MOTION", self.drag_selected, "Move viewport")
        self.bind("M1UP", self.drag_end)

        self.bind('+', lambda: self.window.zoom_in(1.25), "Zoom view in")
        self.bind('=', lambda: self.window.zoom_in(1.25), "Zoom view in")
        self.bind('-', lambda: self.window.zoom_out(0.8), "Zoom view out")
        self.bind('SCROLLUP', lambda: self.window.zoom_in(1.06), "Zoom view in")
        self.bind('SCROLLDOWN', lambda: self.window.zoom_in(0.95), "Zoom view out")
        self.bind('C-0', self.window.reset_zoom, "Reset view position and zoom")

        self.window.add_callback("select", self.begin_control)
        self.window.add_callback("unselect", self.end_control)


    def begin_control(self, obj):
        if obj is not None: 
            obj.begin_control()

    def end_control(self, obj):
        if obj is not None:
            obj.end_control()

    def drag_start(self):
        if self.manager.pointer_obj and self.manager.pointer_obj not in self.window.selected:
            self.window.unselect_all()
            self.window.select(self.manager.pointer_obj)
            raise self.manager.InputNeedsRequeue()

        self.drag_started = True
        self.drag_start_x = self.manager.pointer_ev_x
        self.drag_start_y = self.manager.pointer_ev_y
        self.drag_last_x = self.manager.pointer_ev_x
        self.drag_last_y = self.manager.pointer_ev_y

    def drag_selected(self):
        if self.drag_started is False:
            return

        dx = self.manager.pointer_ev_x - self.drag_last_x
        dy = self.manager.pointer_ev_y - self.drag_last_y

        self.drag_last_x = self.manager.pointer_ev_x
        self.drag_last_y = self.manager.pointer_ev_y

        if self.manager.pointer_obj is None:
            self.window.move_view(dx, dy)

    def drag_end(self):
        self.drag_started = False
        if (self.manager.pointer_obj is None 
            and self.manager.pointer_ev_x == self.drag_start_x
            and self.manager.pointer_ev_y == self.drag_start_y):
            self.window.unselect_all()
