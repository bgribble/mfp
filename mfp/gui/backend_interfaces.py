"""
backend_interfaces.py -- interface declarations for UI classes

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from abc import ABC, abstractmethod
from ..delegate import DelegateMixin, delegatemethod


class BackendInterface:
    _registry = {}
    _interfaces = {}

    def __init_subclass__(cls, *args, **kwargs):
        if BackendInterface in cls.__bases__:
            BackendInterface._interfaces[cls.__name__] = cls
        else:
            for interface in BackendInterface._interfaces.values():
                if interface in cls.__bases__:
                    be_name = getattr(cls, "backend_name", cls.__name__)
                    interface_registry = BackendInterface._registry.setdefault(interface.__name__, {})
                    interface_registry[be_name] = cls

        super().__init_subclass__(*args, **kwargs)

    def setup(self):
        pass

    @classmethod
    def get_backend(cls, backend_name):
        if cls not in BackendInterface._interfaces.values():
            raise ValueError(f"get_backend: class {cls} is not an interface")

        return BackendInterface._registry.get(cls.__name__, {}).get(backend_name)


class InputManagerBackend(ABC, BackendInterface, DelegateMixin):
    @abstractmethod
    @delegatemethod
    def handle_event(self, *args):
        pass



class LayerBackend(ABC, BackendInterface, DelegateMixin):
    @abstractmethod
    @delegatemethod
    def show(self):
        pass

    @abstractmethod
    @delegatemethod
    def hide(self):
        pass



class BaseElementBackend(ABC, BackendInterface, DelegateMixin):
    @abstractmethod
    @delegatemethod
    def move_to_top(self):
        pass

    @abstractmethod
    @delegatemethod
    def update_badge(self):
        pass

    @abstractmethod
    def draw_ports(self):
        pass

    @abstractmethod
    def hide_ports(self):
        pass

    @abstractmethod
    def set_size(self, width, height):
        pass

    @abstractmethod
    @delegatemethod
    def move(self, x, y):
        pass

    @abstractmethod
    @delegatemethod
    def move_z(self, z):
        pass

class ColorDBBackend(ABC, BackendInterface, DelegateMixin):
    @abstractmethod
    @delegatemethod
    def create_from_rgba(self, red, green, blue, alpha):
        pass

    @abstractmethod
    @delegatemethod
    def create_from_name(self, name):
        pass

    @abstractmethod
    @delegatemethod
    def normalize(self, color):
        pass


