"""
backend_interfaces.py -- interface declarations for UI classes

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from mfp import log


class BackendInterface:
    _registry = {}
    _interfaces = {}

    def __init_subclass__(cls, **kwargs):
        '''
        If class directly inherits from BackendInterface, it's an implementation
        base class (an interface). Otherwise, it's an implementation
        of the interface.
        '''
        if BackendInterface in cls.__bases__:
            interface_name = getattr(cls, "interface_name", cls.__name__)
            BackendInterface._interfaces[interface_name] = cls
        else:
            for interface in BackendInterface._interfaces.values():
                if interface in cls.__bases__:
                    interface_name = getattr(interface, "interface_name", interface.__name__)
                    be_name = getattr(cls, "backend_name", cls.__name__)
                    interface_registry = BackendInterface._registry.setdefault(interface_name, {})
                    interface_registry[be_name] = cls

        super().__init_subclass__(**kwargs)

    def setup(self):
        pass

    @classmethod
    def get_backend(cls, backend_name):
        if cls not in BackendInterface._interfaces.values():
            log.debug(f"[get_backend] {BackendInterface._interfaces}")
            raise ValueError(f"get_backend: class {cls} is not an interface")

        interface_name = getattr(cls, "interface_name", cls.__name__)
        backend = BackendInterface._registry.get(interface_name, {}).get(backend_name)
        return backend
