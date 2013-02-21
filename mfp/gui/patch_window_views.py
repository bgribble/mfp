
from ..utils import extends 
from ..main import MFPCommand 
from .tree_display import TreeDisplay
from .patch_window import PatchWindow 
from .patch_element import PatchElement 

@extends(PatchWindow)
def init_object_view(self):
    def get_obj_name(o): 
        from .patch_info import PatchInfo
        if isinstance(o, (PatchElement, PatchInfo)):
            return o.obj_name
        elif isinstance(o, tuple):
            return o[0]

    def obj_name_edited(obj, new_name):
        if isinstance(obj, PatchElement):
            obj.obj_name = new_name
            MFPCommand().rename_obj(obj.obj_id, new_name)
            obj.send_params()
        else:
            oldscopename = obj 
            for l in self.selected_patch.layers:
                if l.scope == oldscopename:
                    l.scope = new_name
            MFPCommand().rename_scope(oldscopename, new_name)
            self.selected_patch.send_params()

    obj_cols = [ ("Name", get_obj_name, True, obj_name_edited, True) ] 
    object_view = TreeDisplay(self.builder.get_object("object_tree"), *obj_cols)
    object_view.select_cb = self._select
    object_view.unselect_cb = self._unselect 

    return object_view 

@extends(PatchWindow)
def init_layer_view(self):
    from .layer import Layer 
    def get_layer_name(o):
        from .patch_info import PatchInfo
        if isinstance(o, Layer):
            return o.name
        elif isinstance(o, PatchInfo):
            return o.obj_name 

    def get_layer_scopename(o):
        if isinstance(o, Layer):
            return o.scope
        else: 
            return ''

    def layer_name_edited(layer, new_value):
        if isinstance(layer, Layer):
            layer.name = new_value
            self.selected_patch.send_params()
            for obj in self.objects:
                if obj.layer == layer:
                    obj.send_params()
        return True

    def layer_scope_edited(layer, new_value):
        if isinstance(layer, Layer):
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


    layer_cols = [("Name", get_layer_name, True, layer_name_edited, False), 
                  ("Scope", get_layer_scopename, True, layer_scope_edited, False)] 
    layer_view = TreeDisplay(self.builder.get_object("layer_tree"), *layer_cols)
    layer_view.select_cb = self._layer_select
    layer_view.unselect_cb = None 

    return layer_view 

