#! /usr/bin/env python
'''
app_window_layer.py
Extra methods to manage the layer display in the main window
'''

from ..utils import extends
from .app_window import AppWindow
from .layer import Layer
from ..gui_main import MFPGUI


@extends(AppWindow)
def layer_select_up(self):
    p = self.selected_patch
    if self.selected_layer in p.layers:
        l = p.layers.index(self.selected_layer)
        self.layer_select(p.layers[l - 1])
    else:
        print("WARNING: selected layer not in selected patch!")
        print(self.selected_layer)
        print(self.selected_patch)


@extends(AppWindow)
def layer_select_down(self):
    p = self.selected_patch
    if self.selected_layer in p.layers:
        l = p.layers.index(self.selected_layer)
        self.layer_select(p.layers[(l + 1) % len(p.layers)])
    else:
        print("WARNING: selected layer not in selected patch!")
        print(self.selected_layer)
        print(self.selected_patch)


@extends(AppWindow)
def layer_select(self, layer):
    if not isinstance(layer, Layer):
        return
    if self.selected_layer is not None:
        self.selected_layer.hide()

    if layer != self.selected_layer:
        sname = layer.scope
        if sname == "__patch__":
            sname = "Patch"
        self.hud_write("Layer: <b>%s</b> (lexical scope '%s')"
                       % (layer.name, sname))
        self.selected_layer = layer

    self.selected_layer.show()
    if self.selected_layer.patch != self.selected_patch:
        self.selected_patch = self.selected_layer.patch


@extends(AppWindow)
def layer_new(self):
    l = Layer.build(self, self.selected_patch, "Layer %d" % len(self.selected_patch.layers))
    self.selected_patch.send_params()
    self.layer_create(l, self.selected_patch)
    self.layer_select(l)
    return True


@extends(AppWindow)
def layer_new_scope(self):
    l = Layer.build(self, self.selected_patch, "Layer %d" % len(self.selected_patch.layers))
    l.scope = l.name.replace(" ", "_").lower()
    MFPGUI().async_task(MFPGUI().mfp.add_scope(self.selected_patch.obj_id, l.scope))
    self.object_view.insert((l.scope, self.selected_patch), self.selected_patch)

    self.selected_patch.send_params()
    self.layer_create(l, self.selected_patch)
    self.layer_select(l)
    return True

@extends(AppWindow)
def layer_move_up(self):
    p = self.selected_patch
    oldpos = p.layers.index(self.selected_layer)

    if oldpos == 0:
        return
    newpos = oldpos-1
    pre = p.layers[:newpos]
    post = [p.layers[newpos]] + p.layers[oldpos+1:]
    p.layers = pre + [self.selected_layer] + post
    self.layer_update(self.selected_layer, p)

@extends(AppWindow)
def layer_move_down(self):
    p = self.selected_patch
    oldpos = p.layers.index(self.selected_layer)
    if oldpos == len(p.layers)-1:
        return

    newpos = oldpos + 1
    pre = p.layers[:oldpos] + [p.layers[newpos]]
    post = p.layers[newpos+1:]
    p.layers = pre + [self.selected_layer] + post

    self.layer_update(self.selected_layer, p)
