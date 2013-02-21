#! /usr/bin/env python
'''
global_mode.py: Global input mode bindings

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode
from mfp import MFPGUI

class GlobalMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window
        InputMode.__init__(self, "Global input bindings")

        # global keybindings
        self.bind("PGUP", self.window.layer_select_up, "Select higher layer")
        self.bind("PGDN", self.window.layer_select_down, "Select lower layer")
        self.bind("C-PGUP", self.window.patch_select_prev, "Select higher patch")
        self.bind("C-PGDN", self.window.patch_select_next, "Select lower patch")

        self.bind('C-s', self.save_file, "Save patch to file")
        self.bind('C-o', self.open_file, "Load file into new patch")
        self.bind('C-f', self.load_file, "Load file into current patch")
        self.bind('C-w', self.window.patch_close, "Close current patch")
        self.bind('C-p', self.window.patch_new, "Create a new patch")

        self.bind('C-e', self.window.toggle_major_mode, "Toggle edit/control")
        self.bind('C-q', self.window.quit, "Quit")

        self.bind("HOVER", self.hover)

    def hover(self):
        if self.manager.pointer_obj is not None:
            self.manager.pointer_obj.show_tip(self.manager.pointer_x, self.manager.pointer_y)
        return False 

    def save_file(self):
        def cb(fname):
            MFPGUI().mfp.save_file(self.window.selected_patch.obj_name, fname)
        self.window.get_prompted_input("File name to save: ", cb)

    def open_file(self):
        def cb(fname):
            MFPGUI().mfp.open_file(fname)
        self.window.get_prompted_input("File name to load: ", cb)

    def load_file(self):
        def cb(fname):
            MFPGUI().mfp.load_file(fname)
        self.window.get_prompted_input("File name to load: ", cb)
