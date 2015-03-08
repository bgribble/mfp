#! /usr/bin/env python
'''
patch_window_select.py
Helper methods for patch window selection

Copyright (c) 2012-2013 Bill Gribble <grib@billgribble.com>
'''

from ..utils import extends
from .patch_window import PatchWindow
from .patch_element import PatchElement
from .patch_info import PatchInfo
from .connection_element import ConnectionElement
from .modes.select_mru import SelectMRUMode
from ..gui_main import MFPGUI

from gi.repository import Gtk, Gdk

@extends(PatchWindow)
def patch_select_prev(self): 
    if not self.selected_patch:
        self.layer_select(self.patches[0].layers[0])
    else:
        pnum = self.patches.index(self.selected_patch)
        pnum -= 1
        self.layer_select(self.patches[pnum].layers[0])

@extends(PatchWindow)
def patch_select_next(self): 
    if not self.selected_patch:
        self.layer_select(self.patches[0].layers[0])
    else:
        pnum = self.patches.index(self.selected_patch)
        pnum = (pnum + 1) % len(self.patches)
        self.layer_select(self.patches[pnum].layers[0])

@extends(PatchWindow)
def patch_close(self):
    from mfp import log 
    p = self.selected_patch
    if p and p.deletable: 
        self.patch_select_next() 
        self.patches.remove(p)
        p.delete()
    else: 
        log.debug("Cannot close window. Close UI via plugin host Edit button")
    if not len(self.patches):
        self.quit()

@extends(PatchWindow)
def patch_new(self):
    MFPGUI().mfp.open_file(None)

@extends(PatchWindow)
def _select(self, obj): 
    if (obj is None) or (not isinstance(obj, PatchElement)) or (obj in self.selected):
        return 
    
    self.selected[:0] = [obj]
    obj.select()

    self.emit_signal("select", obj)

@extends(PatchWindow)
def select(self, obj):
    if obj in self.selected: 
        return True 

    self._select(obj)
    self.object_view.select(obj)
    return True


@extends(PatchWindow)
def _unselect(self, obj):
    if obj is None:
        return 
    if isinstance(obj, PatchElement):
        if obj.edit_mode:
            obj.end_edit()
        obj.end_control()
        obj.unselect()
    if obj in self.selected: 
        self.selected.remove(obj)

    self.emit_signal("unselect", obj)

@extends(PatchWindow)
def unselect(self, obj):
    if obj in self.selected and obj is not None:
        self._unselect(obj)
        self.object_view.unselect(obj)
    return True

@extends(PatchWindow)
def select_all(self):
    self.unselect_all()
    for obj in self.objects:
        if obj.layer == self.active_layer(): 
            self.select(obj)
    return True 

@extends(PatchWindow)
def unselect_all(self):
    oldsel = self.selected 
    self.selected = [] 
    self.object_view.unselect_all()
    for obj in oldsel:
        obj.end_control()
        self._unselect(obj)
    return True


@extends(PatchWindow)
def select_next(self):
    key_obj = None 

    if len(self.selected_layer.objects) == 0:
        return False

    for obj in self.selected: 
        if obj in self.selected_layer.objects: 
            key_obj = obj
            break 

    if (not self.selected or (key_obj is None)):
        start = 0
    else:
        current = self.selected_layer.objects.index(key_obj)
        start = (current + 1) % len(self.selected_layer.objects)
    candidate = start

    for count in range(len(self.selected_layer.objects)):
        if not isinstance(self.selected_layer.objects[candidate], ConnectionElement):
            self.unselect_all()
            self.select(self.selected_layer.objects[candidate])
            return True
        candidate = (candidate + 1) % len(self.selected_layer.objects)
    return False


@extends(PatchWindow)
def select_prev(self):
    key_obj = None 
    if len(self.selected_layer.objects) == 0:
        return False

    for obj in self.selected: 
        if obj in self.selected_layer.objects: 
            key_obj = obj
            break 

    if (not self.selected or (key_obj is None)):
        candidate = -1
    else:
        candidate = self.selected_layer.objects.index(key_obj) - 1

    while candidate > -len(self.selected_layer.objects):
        if not isinstance(self.selected_layer.objects[candidate], ConnectionElement):
            self.unselect_all()
            self.select(self.selected_layer.objects[candidate])
            return True
        candidate -= 1

    return False


@extends(PatchWindow)
def select_mru(self):
    self.input_mgr.enable_minor_mode(SelectMRUMode(self))
    return True


@extends(PatchWindow)
def move_selected(self, dx, dy):
    for obj in self.selected:
        if obj.editable:
            obj.move(max(0, obj.position_x + dx * self.zoom),
                     max(0, obj.position_y + dy * self.zoom))
            if obj.obj_id is not None:
                obj.send_params()
    if self.selected: 
        return True
    else: 
        return False

@extends(PatchWindow)
def delete_selected(self):
    olist = self.selected
    self.unselect_all()
    for o in olist:
        if o.editable:
            o.delete()
    return True

@extends(PatchWindow)
def rezoom(self):
    w, h = self.group.get_size()
    self.group.set_scale_full(self.zoom, self.zoom, w / 2.0, h / 2.0)
    self.group.set_position(self.view_x, self.view_y)
    #self.input_mgr.rezoom()

@extends(PatchWindow)
def reset_zoom(self):
    self.zoom = 1.0
    self.view_x = 0
    self.view_y = 0
    self.rezoom()
    return True


@extends(PatchWindow)
def zoom_out(self, ratio):
    if self.zoom >= 0.1:
        self.zoom *= ratio
        self.rezoom()
    return True


@extends(PatchWindow)
def zoom_in(self, ratio):
    if self.zoom < 20:
        self.zoom *= ratio
        self.rezoom()
    return True


@extends(PatchWindow)
def move_view(self, dx, dy):
    self.view_x += dx
    self.view_y += dy
    self.rezoom()
    return True

@extends(PatchWindow)
def show_selection_box(self, x0, y0, x1, y1): 
    def boxes_overlap(b1, b2): 
        if ((b1[0] >= b2[0]) and (b1[0] <= b2[2])
            or (b2[0] >= b1[0]) and (b2[0] <= b1[2])
            or (b1[2] >= b2[0]) and (b1[2] <= b2[2])
            or (b2[2] >= b1[0]) and (b2[2] <= b1[2])):
            pass
        else:
            return False 
        if ((b1[1] >= b2[1]) and (b1[1] <= b2[3])
            or (b2[1] >= b1[1]) and (b2[1] <= b1[3])
            or (b1[3] >= b2[1]) and (b1[3] <= b2[3])
            or (b2[3] >= b1[1]) and (b2[3] <= b1[3])):
            return True 
        else:
            return False 

    if x0 > x1:
        t = x1; x1 = x0; x0 = t

    if y0 > y1:
        t = y1; y1 = y0; y0 = t

    from gi.repository import Clutter 
    if self.selection_box is None:
        self.selection_box = Clutter.Rectangle()
        self.selection_box.set_border_width(1.0)
        self.selection_box.set_color(self.color_transparent)
        self.selection_box.set_border_color(self.color_unselected)
        self.selection_box_layer = self.selected_layer
        self.selection_box_layer.group.add_actor(self.selection_box)
    elif self.selection_box_layer != self.selected_layer:
        self.selection_box_layer.group.remove_actor(self.selection_box)
        self.selection_box_layer = self.selected_layer
        self.selection_box_layer.group.add_actor(self.selection_box)
    self.selection_box.set_position(x0, y0)
    self.selection_box.set_size(max(1, x1-x0), max(1, y1-y0))
    self.selection_box.show()

    enclosed = [] 
    for obj in self.selected_layer.objects: 
        if obj.parent_id and MFPGUI().recall(obj.parent_id).parent_id:
            continue
        if boxes_overlap((x0, y0, x1, y1),
                         (obj.position_x, obj.position_y, 
                          obj.position_x + obj.width, obj.position_y + obj.height)):
            enclosed.append(obj)

    return enclosed 

@extends(PatchWindow)
def hide_selection_box(self):
    if self.selection_box:
        self.selection_box.destroy()
        self.selection_box = None 

@extends(PatchWindow)
def clipboard_cut(self, pointer_pos):
    if self.selected:
        self.clipboard_copy(pointer_pos)
        self.delete_selected()
        return True 
    else:
        return False 

@extends(PatchWindow)
def clipboard_copy(self, pointer_pos):
    if self.selected:
        cliptxt = MFPGUI().mfp.clipboard_copy(pointer_pos, [o.obj_id for o in self.selected 
                                                            if o.obj_id is not None])
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(cliptxt, -1)
        return True 
    else:
        return False 



@extends(PatchWindow)
def clipboard_paste(self, pointer_pos=None):
    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    cliptxt = clipboard.wait_for_text()
    if not cliptxt: 
        return False 
    
    newobj = MFPGUI().mfp.clipboard_paste(cliptxt, self.selected_patch.obj_id, 
                                          self.selected_layer.scope, None)

    def paste_select_helper():
        for o in newobj:
            obj = MFPGUI().recall(o)
            if obj is None:
                return True 
            if not isinstance(obj, PatchInfo):
                obj.move_to_layer(self.selected_layer)
            if obj not in self.selected: 
                self.select(MFPGUI().recall(o))
        return False 

    if newobj is not None:
        self.unselect_all()
        MFPGUI().clutter_do(paste_select_helper)

        return True 
    else:
        return False 

