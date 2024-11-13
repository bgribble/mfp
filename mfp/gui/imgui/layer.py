from mfp import log
from mfp.gui.base_element import BaseElement
from mfp.gui.layer import Layer, LayerImpl


class ImguiLayerImpl(Layer, LayerImpl):
    backend_name = "imgui"

    def __init__(self, app_window, patch, name, scope="__patch__"):
        super().__init__(app_window, patch, name, scope)
        self.patch.layers.append(self)

    def show(self):
        pass 

    def hide(self):
        pass

    def remove(self, obj):
        super().remove(obj)

    def add(self, obj, container=None):
        super().add(obj, container=container)
        if container and hasattr(container, "child_elements"):
            container.child_elements.append(obj)

    def delete(self):
        pass
