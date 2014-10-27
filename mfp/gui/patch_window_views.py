
from ..utils import extends 
from ..mfp_command import MFPCommand 
from .tree_display import TreeDisplay
from .patch_window import PatchWindow 
from .patch_element import PatchElement 
from .patch_info import PatchInfo 
from .layer import Layer 

@extends(PatchWindow)
def init_object_view(self):
    def get_obj_name(o): 
        if isinstance(o, PatchElement):
            return o.obj_name
        elif isinstance(o, PatchInfo):
            return "%s (%s)" % (o.obj_name, o.context_name)
        elif isinstance(o, tuple):
            return o[0]

    def obj_name_edited(obj, new_name):
        if isinstance(obj, (PatchElement, PatchInfo)):
            obj.obj_name = new_name
            MFPCommand().rename_obj(obj.obj_id, new_name)
            obj.send_params()
        else:
            oldscopename = obj 
            for l in self.selected_patch.layers:
                if l.scope == oldscopename:
                    l.scope = new_name
            MFPCommand().rename_scope(self.selected_patch.obj_id, oldscopename, new_name)
            self.selected_patch.send_params()

        if isinstance(obj, PatchElement):
            parent = (obj.layer.scope, obj.layer.patch) 
        elif isinstance(obj, PatchInfo): 
            parent = None 
        else: 
            parent = (self.selected_layer,)

        self.object_view.update(obj, parent)

    def obj_selected(obj):
        self._select(obj)
        if isinstance(obj, PatchElement): 
            self.layer_select(obj.layer)
        elif isinstance(obj, PatchInfo):
            self.layer_select(obj.layers[0])
        elif isinstance(obj, tuple):
            scope = obj[0]
            patch = obj[1] 
            for l in patch.layers:
                if l.scope == scope:
                    self.layer_select(l)
                    return 
            self.layer_select(patch.layers[0])

    obj_cols = [ ("Name", get_obj_name, True, obj_name_edited, True) ] 
    object_view = TreeDisplay(self.builder.get_object("object_tree"), True, *obj_cols)
    object_view.select_cb = obj_selected
    object_view.unselect_cb = self._unselect 

    return object_view 

@extends(PatchWindow)
def init_layer_view(self):
    def get_sortname(o): 
        if isinstance(o, Layer):
            return o.patch.obj_name + ':%04d' % o.patch.layers.index(o) 
        elif isinstance(o, PatchInfo):
            return "%s (%s)" % (o.obj_name, o.context_name) 

    def get_layer_name(o):
        if isinstance(o, Layer):
            return o.name
        elif isinstance(o, PatchInfo):
            return "%s (%s)" % (o.obj_name, o.context_name) 

    def get_layer_scopename(o):
        if isinstance(o, Layer):
            return o.scope
        else: 
            return ''

    def layer_name_edited(obj, new_value):
        if isinstance(obj, Layer):
            obj.name = new_value
            self.selected_patch.send_params()
            for lobj in self.objects:
                if lobj.layer == obj:
                    lobj.send_params()
        elif isinstance(obj, (PatchElement, PatchInfo)):
            obj.obj_name = new_value
            MFPCommand().rename_obj(obj.obj_id, new_value)
            obj.send_params()
        return True

    def layer_scope_edited(layer, new_value):
        from mfp import log
        if isinstance(layer, Layer):
            p = self.selected_patch
            if not p.has_scope(new_value):
                log.debug("Adding scope", new_value, "to patch", self.selected_patch)
                MFPCommand().add_scope(self.selected_patch.obj_id, new_value)

            layer.scope = new_value
            self.selected_patch.send_params()
            for obj in self.objects:
                if obj.obj_id is not None and obj.layer == layer:
                    MFPCommand().set_scope(obj.obj_id, new_value)
                    self.refresh(obj)
        return True

    def sel_layer(l):
        if isinstance(l, PatchInfo):
            self.layer_view.select(None)
            self.layer_select(l.layers[0])
        else:
            self._layer_select(l)

    layer_cols = [("Name", get_layer_name, True, layer_name_edited, get_sortname), 
                  ("Scope", get_layer_scopename, True, layer_scope_edited, False)] 
    layer_view = TreeDisplay(self.builder.get_object("layer_tree"), False, *layer_cols)
    layer_view.select_cb = sel_layer
    layer_view.unselect_cb = None

    return layer_view 

