from gi.repository import Clutter
from mfp.gui.base_element import BaseElement
from mfp.gui.layer import Layer, LayerImpl


class ClutterLayerImpl(Layer, LayerImpl):
    backend_name = "clutter"

    def __init__(self, app_window, patch, name, scope="__patch__"):
        super().__init__(app_window, patch, name, scope)
        self.container = self.app_window.group
        self.group = Clutter.Group()
        self.patch.layers.append(self)

        if not self.app_window.layer_view.in_tree(self):
            self.app_window.layer_view.insert(self, self.patch)

    def show(self):
        if self.container and self.group:
            self.container.add_child(self.group)

    def hide(self):
        if self.group in self.container.get_children():
            self.container.remove_child(self.group)

    def remove(self, obj):
        super().remove(obj)

        if isinstance(obj, BaseElement):
            child = obj.group
            obj.parent = None
        else:
            child = obj

        parent = child.get_parent()
        if parent:
            parent.remove_child(child)

    def add(self, obj, container=None):
        super().add(obj, container=container)

        if isinstance(obj, BaseElement):
            group = obj.group
        else:
            group = obj.backend.group

        dest_group = (container and container.group) or self.group

        parent = group.get_parent()
        child = group
        if parent != dest_group:
            if parent:
                parent.remove_child(child)
            dest_group.add_child(child)

    def delete(self):
        del self.group
        self.group = None
