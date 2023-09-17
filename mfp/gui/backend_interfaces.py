from abc import ABC, abstractmethod
from ..delegate import DelegateMixin, delegatemethod


class AppWindowBackend(ABC, DelegateMixin):
    backend_registry = {}

    def __init_subclass__(cls, *args, **kwargs):
        AppWindowBackend.backend_registry[getattr(cls, "backend_name", cls.__name__)] = cls
        super().__init_subclass__(*args, **kwargs)
    
    @staticmethod
    def get_backend(backend_name):
        # return a concrete impl based on the backend name
        return AppWindowBackend.backend_registry.get(backend_name)

    #####################
    # backend control 

    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def shutdown(self):
        pass

    @abstractmethod
    def render(self):
        pass

    @abstractmethod
    @delegatemethod
    def grab_focus(self):
        pass

    #####################
    # coordinate transforms and zoom

    @abstractmethod
    def screen_to_canvas(self, x, y):
        pass

    @abstractmethod
    def canvas_to_screen(self, x, y):
        pass

    @abstractmethod
    @delegatemethod
    def rezoom(self):
        pass

    #####################
    # element operations 

    @abstractmethod
    def register(self, element):
        pass

    @abstractmethod
    def unregister(self, element):
        pass

    @abstractmethod
    def refresh(self, element):
        pass

    @abstractmethod
    def select(self, element):
        pass

    @abstractmethod
    def unselect(self, element):
        pass

    #####################
    # autoplace 

    @abstractmethod
    @delegatemethod
    def show_autoplace_marker(self, x, y):
        pass

    @abstractmethod
    @delegatemethod
    def hide_autoplace_marker(self):
        pass

    #####################
    # HUD/console 

    @abstractmethod
    @delegatemethod
    def hud_banner(self, message, display_time=3.0):
        pass

    @abstractmethod
    @delegatemethod
    def hud_write(self, message, display_time=3.0):
        pass

    @abstractmethod
    @delegatemethod
    def hud_set_prompt(self, prompt, default=''):
        pass

    @abstractmethod
    @delegatemethod
    def console_activate(self):
        pass

    #####################
    # clipboard

    @abstractmethod
    @delegatemethod
    def clipboard_cut(self, pointer_pos):
        pass

    @abstractmethod
    @delegatemethod
    def clipboard_copy(self, pointer_pos):
        pass

    @abstractmethod
    @delegatemethod
    def clipboard_paste(self, pointer_pos=None):
        pass

    #####################
    # selection box

    @abstractmethod
    @delegatemethod
    def show_selection_box(self, x0, y0, x1, y1):
        pass

    @abstractmethod
    @delegatemethod
    def hide_selection_box(self):
        pass

    #####################
    # log output

    @abstractmethod
    @delegatemethod
    def log_write(self, message, level):
        pass
    
    #####################
    # key bindings display

    @abstractmethod
    @delegatemethod
    def display_bindings(self):
        pass

