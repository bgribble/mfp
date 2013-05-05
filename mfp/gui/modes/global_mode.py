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

        self.bind('C-f', self.window.patch_new, "Create a new patch")
        self.bind('C-o', self.open_file, "Load file into new patch")
        self.bind('C-s', self.save_file, "Save patch to file")
        self.bind('C-w', self.window.patch_close, "Close current patch")

        self.bind('C-q', self.window.quit, "Quit")

        self.bind("HOVER", self.hover)

    def hover(self):
        if self.manager.pointer_obj is not None:
            self.manager.pointer_obj.show_tip(self.manager.pointer_x, self.manager.pointer_y)
        return False 

    def save_file(self):
        patch = self.window.selected_patch
        if patch.last_filename is None: 
            default_filename = patch.obj_name + '.mfp'
        else:
            default_filename = patch.last_filename 

        def cb(fname):
            if fname:
                patch.last_filename = fname 
                if fname != default_filename:
                    newname ='.'.join(fname.split(".")[:-1]) 
                    patch.obj_name = newname
                    MFPGUI().mfp.rename_obj(patch.obj_id, newname)
                    patch.send_params()
                    self.window.refresh(patch)
                MFPGUI().mfp.save_file(patch.obj_name, fname)
        self.window.get_prompted_input("File name to save: ", cb, default_filename)

    def open_file(self):
        def cb(fname):
            MFPGUI().mfp.open_file(fname)
        self.window.get_prompted_input("File name to load: ", cb)
