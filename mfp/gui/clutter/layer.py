from gi.repository import Clutter
from mfp.gui.base_element import BaseElement
from ..backend_interfaces import LayerBackend

from mfp import log


class ClutterLayerBackend(LayerBackend):
    backend_name = "clutter"

    def __init__(self, layer):
        self.layer = layer
        self.app_window = layer.app_window
        self.container = self.app_window.backend.group
        self.group = Clutter.Group()

        super().__init__(layer)

    def show(self):
        self.container.add_child(self.group)

    def hide(self):
        if self.group in self.container.get_children():
            self.container.remove_child(self.group)

    def remove(self, obj):
        if isinstance(obj, BaseElement):
            child = obj.group
            obj.parent = None
        else:
            child = obj

        parent = child.get_parent()
        if parent:
            parent.remove_child(child)

    def add(self, obj, container=None):
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
