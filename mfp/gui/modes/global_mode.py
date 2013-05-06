#! /usr/bin/env python
'''
global_mode.py: Global input mode bindings

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode
from ..message_element import TransientMessageElement
from mfp import MFPGUI

class GlobalMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window
        
        self.allow_selection_drag = True 
        self.selection_drag_started = False 
        self.drag_started = False
        self.selbox_started = False 
        self.selbox_changed = [] 
        self.drag_start_x = None
        self.drag_start_y = None
        self.drag_last_x = None
        self.drag_last_y = None
        self.drag_target = None

        InputMode.__init__(self, "Global input bindings")

        # global keybindings
        self.bind("!", self.transient_msg, "Send message to selection")

        self.bind("PGUP", self.window.layer_select_up, "Select higher layer")
        self.bind("PGDN", self.window.layer_select_down, "Select lower layer")
        self.bind("C-PGUP", self.window.patch_select_prev, "Select higher patch")
        self.bind("C-PGDN", self.window.patch_select_next, "Select lower patch")

        self.bind('C-f', self.window.patch_new, "Create a new patch")
        self.bind('C-o', self.open_file, "Load file into new patch")
        self.bind('C-s', self.save_file, "Save patch to file")
        self.bind('C-w', self.window.patch_close, "Close current patch")
        self.bind('C-q', self.window.quit, "Quit")

        self.bind("M1DOWN", lambda: self.selbox_start(None), "Start selection box")
        self.bind("M1-MOTION", lambda: self.selbox_motion(True), "Drag selection box")
        self.bind("M1UP", self.selbox_end, "End selection box")

        self.bind("S-M1DOWN", lambda: self.selbox_start(True), "Start add-to-selection box")
        self.bind("S-M1-MOTION", lambda: self.selbox_motion(True), "Drag add-to-selection box")
        self.bind("S-M1UP", self.selbox_end, "End selection box")

        self.bind("C-M1DOWN", lambda: self.selbox_start(False), "Start toggle-selection box")
        self.bind("C-M1-MOTION", lambda: self.selbox_motion(False), "Drag toggle-selection box")
        self.bind("C-M1UP", self.selbox_end, "End toggle-selection box")

        self.bind("S-C-M1DOWN", self.drag_start, "Begin dragging viewport")
        self.bind("S-C-M1-MOTION", self.drag_motion, "Drag viewport")
        self.bind("S-C-M1UP", self.drag_end, "End drag viewport")

        self.bind('+', lambda: self.window.zoom_in(1.25), "Zoom view in")
        self.bind('=', lambda: self.window.zoom_in(1.25), "Zoom view in")
        self.bind('-', lambda: self.window.zoom_out(0.8), "Zoom view out")
        self.bind('SCROLLUP', lambda: self.window.zoom_in(1.06), "Zoom view in")
        self.bind('SCROLLDOWN', lambda: self.window.zoom_in(0.95), "Zoom view out")
        self.bind('C-0', self.window.reset_zoom, "Reset view position and zoom")
        self.bind("HOVER", lambda: self.hover(False))
        self.bind("S-HOVER", lambda: self.hover(True))

    def transient_msg(self):
        if self.window.selected is not None:
            return self.window.add_element(TransientMessageElement)
        else:
            return False

    def hover(self, details):
        if self.manager.pointer_obj is not None:
            self.manager.pointer_obj.show_tip(self.manager.pointer_x, self.manager.pointer_y,
                                             details)
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


    def drag_start(self):
        self.drag_started = True 
        px = self.manager.pointer_ev_x
        py = self.manager.pointer_ev_y

        self.drag_last_x = px
        self.drag_last_y = py
        return True

    def drag_motion(self):
        if self.drag_started is False:
            return False 

        px = self.manager.pointer_ev_x
        py = self.manager.pointer_ev_y

        dx = px - self.drag_last_x
        dy = py - self.drag_last_y

        self.drag_last_x = px
        self.drag_last_y = py

        self.window.move_view(dx, dy)
        return True

    def drag_end(self):
        self.drag_started = False
        return True

    def selbox_start(self, select_mode):
        if select_mode is None:
            if self.manager.pointer_obj is not None:
                if self.manager.pointer_obj not in self.window.selected: 
                    self.window.unselect_all()
                self.window.select(self.manager.pointer_obj)
                if self.allow_selection_drag:
                    self.selection_drag_started = True 
            else: 
                self.window.unselect_all()
                self.selbox_started = True 
        elif select_mode is True: 
            if (self.manager.pointer_obj
                and self.manager.pointer_obj not in self.window.selected):
                self.window.select(self.manager.pointer_obj)
            self.selbox_started = True 
        else: 
            if self.manager.pointer_obj in self.window.selected:
                self.window.unselect(self.manager.pointer_obj)
            self.selbox_started = True 

        px = self.manager.pointer_x
        py = self.manager.pointer_y

        self.drag_start_x = px
        self.drag_start_y = py
        self.drag_last_x = px
        self.drag_last_y = py
        return True

    def selbox_motion(self, select_mode): 
        if not (self.selbox_started or self.selection_drag_started):
            return False 

        px = self.manager.pointer_x
        py = self.manager.pointer_y
        dx = px - self.drag_last_x
        dy = py - self.drag_last_y 
        self.drag_last_x = px
        self.drag_last_y = py

        if self.selection_drag_started: 
            for obj in self.window.selected:
                obj.drag(dx, dy)
            return True 

        enclosed = self.window.show_selection_box(self.drag_start_x, self.drag_start_y, 
                                                  self.drag_last_x, self.drag_last_y)

        for obj in enclosed:
            if select_mode:
                if obj not in self.window.selected:
                    if obj not in self.selbox_changed:
                        self.selbox_changed.append(obj)
                    self.window.select(obj)
            else:
                if obj not in self.selbox_changed:
                    self.selbox_changed.append(obj)
                    if obj in self.window.selected:
                        self.window.unselect(obj)
                    else: 
                        self.window.select(obj)
        new_changed = []
        for obj in self.selbox_changed: 
            if obj not in enclosed:
                if obj in self.window.selected:
                    self.window.unselect(obj)
                else: 
                    self.window.select(obj)
            else:
                new_changed.append(obj)
        self.selbox_changed = new_changed 

        return True

    def selbox_end(self):
        self.selbox_started = False
        self.selection_drag_started = False 
        self.selbox_changed = [] 
        self.window.hide_selection_box()
        return True

