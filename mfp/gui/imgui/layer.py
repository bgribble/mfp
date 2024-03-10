
from mfp.gui.base_element import BaseElement
from mfp.gui.layer import Layer, LayerImpl


class ImguiLayerImpl(Layer, LayerImpl):
    backend_name = "imgui"

    def __init__(self, app_window, patch, name, scope="__patch__"):
        super().__init__(app_window, patch, name, scope)
        self.patch.layers.append(self)

        #if not self.app_window.layer_view.in_tree(self):
        #    self.app_window.layer_view.insert(self, self.patch)

    def show(self):
        #if self.container and self.group:
        #    self.container.add_child(self.group)
        pass 

    def hide(self):
        #if self.group in self.container.get_children():
        #    self.container.remove_child(self.group)
        pass

    def remove(self, obj):
        super().remove(obj)

    def add(self, obj, container=None):
        super().add(obj, container=container)

    def delete(self):
        pass
