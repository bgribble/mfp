#! /usr/bin/env python
'''
app_window_select.py
Helper methods for patch window selection

Copyright (c) 2012-2013 Bill Gribble <grib@billgribble.com>
'''

from ..utils import extends
from .app_window import AppWindow
from .base_element import BaseElement
from .connection_element import ConnectionElement
from .modes.select_mru import SelectMRUMode
from ..gui_main import MFPGUI
from mfp import log


@extends(AppWindow)
def patch_select_prev(self):
    if not self.selected_patch:
        patch = self.patches[0]
    else:
        pnum = self.patches.index(self.selected_patch)
        pnum -= 1
        patch = self.patches[pnum]

    if patch.selected_layer:
        layer = patch.selected_layer
    else:
        layer = patch.layers[0]
    self.layer_select(layer)


@extends(AppWindow)
def patch_select_next(self):
    if not self.patches:
        return None

    patch = None
    if len(self.patches) == 1 or not self.selected_patch:
        patch = self.patches[0]
    elif self.selected_patch in self.patches:
        pnum = self.patches.index(self.selected_patch)
        pnum = (pnum + 1) % len(self.patches)
        patch = self.patches[pnum]

    if not patch:
        return

    if patch.selected_layer:
        layer = patch.selected_layer
    else:
        layer = patch.layers[0]
    self.layer_select(layer)


@extends(AppWindow)
async def patch_close(self, patch=None, delete_obj=True, allow_quit=True):
    if patch:
        p = patch
    else:
        p = self.selected_patch

    if p and p.deletable:
        self.patch_select_next()
        if p in self.patches:
            self.patches.remove(p)
        await p.delete(delete_obj=delete_obj)
    else:
        log.debug("Cannot close window. Close UI via plugin host Edit button")

    if allow_quit and not len(self.patches) > 0:
        await self.quit()


@extends(AppWindow)
async def patch_new(self):
    """
    patch_new creates a new patch starting from the UI.

    The flow is that we ask the main app to create a new (empty) file,
    then it requests that the app create a new patch display.
    """
    await MFPGUI().mfp.open_file(None)


@extends(AppWindow)
async def select(self, obj):
    if (obj is None) or (not isinstance(obj, BaseElement)):
        return

    if obj not in self.selected:
        self.selected = [obj] + self.selected
    obj.select()
    await self.signal_emit("select", obj)
    return True


@extends(AppWindow)
async def unselect(self, obj):
    if obj is None:
        return

    if isinstance(obj, BaseElement):
        if obj.edit_mode:
            await obj.end_edit()
        obj.end_control()
        obj.unselect()
        await self.signal_emit("unselect", obj)

    if obj in self.selected:
        self.selected.remove(obj)
    return True


@extends(AppWindow)
async def select_all(self):
    await self.unselect_all()
    for obj in self.objects:
        if obj.layer == self.active_layer():
            await self.select(obj)
    return True


@extends(AppWindow)
async def unselect_all(self):
    oldsel = [*self.selected]
    for obj in oldsel:
        obj.end_control()
        await self.unselect(obj)
    self.selected = []
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
            await self.select(self.selected_layer.objects[candidate])
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
            await self.select(self.selected_layer.objects[candidate])
            return True
        candidate -= 1

    return False


@extends(AppWindow)
async def select_mru(self):
    self.input_mgr.enable_minor_mode(SelectMRUMode(self))
    return True


@extends(AppWindow)
async def move_selected(self, dx, dy):
    for obj in self.selected:
        if obj.editable and obj.display_type != 'connection':
            await obj.move(
                obj.position_x + dx * self.selected_patch.display_info.view_zoom,
                obj.position_y + dy * self.selected_patch.display_info.view_zoom
            )
            if obj.obj_id is not None:
                obj.send_params()
    if self.selected:
        return True
    else:
        return False


@extends(AppWindow)
async def delete_selected(self):
    olist = [*self.selected]
    await self.unselect_all()
    for o in olist:
        if o.editable:
            await o.delete()
    return True


@extends(AppWindow)
def reset_zoom(self):
    di = self.selected_patch.display_info
    di.view_zoom = 1.0
    di.view_x = 0
    di.view_y = 0
    self.viewport_pos_set = True
    self.viewport_zoom_set = True
    self.rezoom()
    return True


@extends(AppWindow)
def relative_zoom(self, ratio):
    di = self.selected_patch.display_info
    candidate_zoom = ratio * di.view_zoom
    if 0.1 <= candidate_zoom <= 20:
        orig_zoom = di.view_zoom
        di.view_zoom = candidate_zoom
        self.rezoom(previous=orig_zoom)
        self.viewport_pos_set = True
        self.viewport_zoom_set = True
    return True


@extends(AppWindow)
def move_view(self, dx, dy):
    di = self.selected_patch.display_info
    di.view_x += dx
    di.view_y += dy
    self.viewport_pos_set = True
    self.rezoom()
    return True
