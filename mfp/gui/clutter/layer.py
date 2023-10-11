from gi.repository import Clutter
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
        self.group.remove_actor(obj)
        obj.parent = None

    def add(self, obj):
        parent = obj.get_parent()
        if parent != self.group:
            if parent:
                parent.remove_actor(obj)
            self.group.add_actor(obj)

    def delete(self):
        del self.group
        self.group = None
