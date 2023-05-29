from abc import ABC, abstractmethod


class AppWindowBackend(ABC):

    backend_registry = {}

    def __init_subclass__(cls, *args, **kwargs):
        AppWindowBackend.backend_registry[getattr(cls, "backend_name", cls.__name__)] = cls
        super().__init_subclass__(*args, **kwargs)
    
    @abstractmethod
    def shutdown(self):
        pass

    @abstractmethod
    def init_input(self):
        pass

    @abstractmethod
    def log_write(self, message, level):
        pass

    @abstractmethod
    def show_autoplace_marker(self, x, y):
        pass

    @abstractmethod
    def hide_autoplace_marker(self):
        pass

    @abstractmethod
    def hud_banner(self, message, display_time=3.0):
        pass

    @abstractmethod
    def hud_set_prompt(self, prompt, default=''):
        pass

    @abstractmethod
    def console_activate(self):
        pass

    @abstractmethod
    def clipboard_cut(self, pointer_pos):
        pass

    @abstractmethod
    def clipboard_copy(self, pointer_pos):
        pass

    @abstractmethod
    def clipboard_paste(self, pointer_pos=None):
        pass

    @abstractmethod
    def rezoom(self):
        pass

    @abstractmethod
    def select(self, element):
        pass

    @abstractmethod
    def unselect(self, element):
        pass

    @staticmethod
    def get_backend(backend_name):
        # return a concrete impl based on the backend name
        return AppWindowBackend.backend_registry.get(backend_name)


