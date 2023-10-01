#! /usr/bin/env python
'''
patch_window_select.py
Helper methods for patch window selection

Copyright (c) 2012-2013 Bill Gribble <grib@billgribble.com>
'''

from ..utils import extends
from .patch_window import AppWindow
from .patch_element import PatchElement
from .connection_element import ConnectionElement
from .modes.select_mru import SelectMRUMode
from ..gui_main import MFPGUI
from mfp import log


@extends(AppWindow)
def patch_select_prev(self):
    if not self.selected_patch:
        self.layer_select(self.patches[0].layers[0])
    else:
        pnum = self.patches.index(self.selected_patch)
        pnum -= 1
        self.layer_select(self.patches[pnum].layers[0])


@extends(AppWindow)
def patch_select_next(self):
    if not self.selected_patch:
        self.layer_select(self.patches[0].layers[0])
    else:
        pnum = self.patches.index(self.selected_patch)
        pnum = (pnum + 1) % len(self.patches)
        self.layer_select(self.patches[pnum].layers[0])


@extends(AppWindow)
async def patch_close(self):
    p = self.selected_patch
    if p and p.deletable:
        self.patch_select_next()
        self.patches.remove(p)
        await p.delete()
    else:
        log.debug("Cannot close window. Close UI via plugin host Edit button")
    if not len(self.patches):
        await self.quit()


@extends(AppWindow)
async def patch_new(self):
    MFPGUI().mfp.open_file.sync(None)


@extends(AppWindow)
def _select(self, obj):
    if (obj is None) or (not isinstance(obj, PatchElement)) or (obj in self.selected):
        return

    self.selected[:0] = [obj]
    obj.select()

    self.backend.select(obj)
    self.emit_signal("select", obj)


@extends(AppWindow)
def select(self, obj):
    if obj in self.selected:
        return True

    self._select(obj)
    return True


@extends(AppWindow)
async def _unselect(self, obj):
    if obj is None:
        return
    if isinstance(obj, PatchElement):
        if obj.edit_mode:
            await obj.end_edit()
        obj.end_control()
        obj.unselect()
    if obj in self.selected:
        self.selected.remove(obj)

    self.backend.unselect(obj)
    self.emit_signal("unselect", obj)


@extends(AppWindow)
async def unselect(self, obj):
    if obj in self.selected and obj is not None:
        await self._unselect(obj)
    return True


@extends(AppWindow)
async def select_all(self):
    await self.unselect_all()
    for obj in self.objects:
        if obj.layer == self.active_layer():
            self.select(obj)
    return True


@extends(AppWindow)
async def unselect_all(self):
    oldsel = self.selected
    self.selected = []
    for obj in oldsel:
        obj.end_control()
        await self._unselect(obj)
    return True


@extends(AppWindow)
async def select_next(self):
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
            await self.unselect_all()
            self.select(self.selected_layer.objects[candidate])
            return True
        candidate = (candidate + 1) % len(self.selected_layer.objects)
    return False


@extends(AppWindow)
async def select_prev(self):
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
            await self.unselect_all()
            self.select(self.selected_layer.objects[candidate])
            return True
        candidate -= 1

    return False


@extends(AppWindow)
def select_mru(self):
    self.input_mgr.enable_minor_mode(SelectMRUMode(self))
    return True


@extends(AppWindow)
def move_selected(self, dx, dy):
    for obj in self.selected:
        if obj.editable and obj.display_type != 'connection':
            obj.move(max(0, obj.position_x + dx * self.zoom),
                     max(0, obj.position_y + dy * self.zoom))
            if obj.obj_id is not None:
                obj.send_params()
    if self.selected:
        return True
    else:
        return False


@extends(AppWindow)
async def delete_selected(self):
    olist = self.selected
    await self.unselect_all()
    for o in olist:
        if o.editable:
            await o.delete()
    return True


@extends(AppWindow)
def reset_zoom(self):
    self.zoom = 1.0
    self.view_x = 0
    self.view_y = 0
    self.rezoom()
    return True


@extends(AppWindow)
def zoom_out(self, ratio):
    if self.zoom >= 0.1:
        self.zoom *= ratio
        self.rezoom()
    return True


@extends(AppWindow)
def zoom_in(self, ratio):
    if self.zoom < 20:
        self.zoom *= ratio
        self.rezoom()
    return True


@extends(AppWindow)
def move_view(self, dx, dy):
    self.view_x += dx
    self.view_y += dy
    self.rezoom()
    return True
