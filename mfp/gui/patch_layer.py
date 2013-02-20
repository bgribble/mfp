#! /usr/bin/env python
'''
patch_layer.py
A layer in the patch window
'''

from ..utils import extends
from gi.repository import Clutter
from ..main import MFPCommand
from .patch_window import PatchWindow 

class PatchLayer(object):
    def __init__(self, stage, patch, name, scope="__patch__"):
        self.stage = stage
        self.patch = patch
        self.name = name
        self.scope = scope
        self.objects = []
        self.group = Clutter.Group()

    def show(self):
        self.stage.group.add_actor(self.group)

    def hide(self):
        self.stage.group.remove_actor(self.group)

    def resort(self, obj):
        if obj in self.objects:
            self.objects.remove(obj)
        self.add(obj)

    def add(self, obj):
        BAD = 1000000
        obj.layer = self

        def distance(left, right):
            d1 = ((obj.position_x - left.position_x) ** 2
                  + (obj.position_y - left.position_y) ** 2) ** 0.5
            d2 = ((obj.position_x - right.position_x) ** 2
                  + (obj.position_y - right.position_y) ** 2) ** 0.5
            return d1 + d2

        if not len(self.objects):
            self.objects = [obj]
        elif ((obj.position_x < self.objects[0].position_x)
              and (obj.position_y < self.objects[0].position_y)):
            self.objects[:0] = [obj]
        elif ((obj.position_x > self.objects[-1].position_x)
              and (obj.position_y > self.objects[-1].position_y)):
            self.objects.append(obj)
        else:
            distances = []
            for i in range(len(self.objects) - 1):
                distances.append(distance(self.objects[i], self.objects[i + 1]))

            if ((obj.position_x < self.objects[0].position_x)
                    or (obj.position_y < self.objects[0].position_y)):
                distances[0:0] = [distance(self.objects[0], self.objects[0])]
            else:
                distances[0:0] = [BAD]

            if ((obj.position_x > self.objects[-1].position_x)
                    or (obj.position_y > self.objects[-1].position_y)):
                distances.append(distance(self.objects[-1], self.objects[-1]))
            else:
                distances.append(BAD)

            newloc = distances.index(min(distances))
            self.objects[newloc:newloc] = [obj]

    def remove(self, obj):
        if obj in self.objects:
            self.objects.remove(obj)
        obj.layer = None



@extends(PatchWindow)
def layer_name_edited(self, layer, new_value):
    if isinstance(layer, PatchLayer):
        layer.name = new_value
        self.selected_patch.send_params()
        for obj in self.objects:
            if obj.layer == layer:
                obj.send_params()
    return True


@extends(PatchWindow)
def layer_scope_edited(self, layer, new_value):
    if isinstance(layer, PatchLayer):
        p = self.selected_patch
        layer.scope = new_value
        if not p.has_scope(new_value):
            MFPCommand().add_scope(new_value)

        self.selected_patch.send_params()
        for obj in self.objects:
            if obj.layer == layer:
                MFPCommand().set_scope(obj.obj_id, new_value)
                self.refresh(obj)
    return True


@extends(PatchWindow)
def layer_select_up(self):
    p = self.selected_patch
    l = p.layers.index(self.selected_layer)
    self.layer_select(p.layers[l - 1])


@extends(PatchWindow)
def layer_select_down(self):
    p = self.selected_patch
    l = p.layers.index(self.selected_layer)
    self.layer_select(p.layers[(l + 1) % len(p.layers)])


@extends(PatchWindow)
def layer_select(self, layer):
    self._layer_select(layer)
    self.layer_view.select(layer)

@extends(PatchWindow)
def _layer_select(self, layer):
    if not isinstance(layer, PatchLayer): 
        return 
    if self.selected_layer is not None:
        self.selected_layer.hide()
    self.selected_layer = layer
    self.selected_layer.show()
    sname = self.selected_layer.scope
    if sname == "__patch__":
        sname = "Patch"
    self.hud_write("Layer: <b>%s</b> (lexical scope '%s')" % (self.selected_layer.name, sname))



@extends(PatchWindow)
def layer_new(self):
    l = PatchLayer(self, self.selected_patch, "Layer %d" % len(self.selected_patch.layers))
    self.selected_patch.layers.append(l)
    self.selected_patch.send_params()
    self.layer_view.insert(l, self.selected_patch)
    self.layer_select(l)
    return True


@extends(PatchWindow)
def layer_new_scope(self):
    l = PatchLayer(self, self.selected_patch, "Layer %d" % len(self.selected_patch.layers))
    l.scope = l.name.replace(" ", "_").lower()
    MFPCommand().add_scope(l.scope)
    self.layer_view.insert(l, self.selected_patch)
    self.object_view.insert((l.scope, self.selected_patch), self.selected_patch)

    self.selected_patch.layers.append(l)
    self.selected_patch.send_params()
    self.layer_select(l)
    return True

@extends(PatchWindow)
def layer_move_up(self):
    p = self.selected_patch
    oldpos = p.layers.index(self.selected_layer)
    if oldpos == 0:
        return 
    
    newpos = oldpos-1
    friend = p.layers[newpos]
    pre = p.layers[:newpos]
    post = [p.layers[newpos]] + p.layers[oldpos+1:]
    p.layers = pre + [self.selected_layer] + post 

    self.layer_view.move_before(self.selected_layer, friend)

@extends(PatchWindow)
def layer_move_down(self):
    p = self.selected_patch
    oldpos = p.layers.index(self.selected_layer)
    if oldpos == len(p.layers)-1:
        return 

    newpos = oldpos + 1
    friend = p.layers[newpos]
    pre = p.layers[:oldpos] + [p.layers[newpos]]
    post = p.layers[newpos+1:]
    p.layers = pre + [self.selected_layer] + post 
    
    self.layer_view.move_after(self.selected_layer, friend)


