
from .backend_interfaces import TextWidgetBackend
from ..gui_main import MFPGUI


class TextWidget:
    """
    TextWidget: A wrapper around the backend's editable label

    Uses simple markup to style text, just using Pango for
    the Clutter backend and emulating it in others
    """
    def __init__(self, element):
        self.container = element

        # FIXME element should have a backend but doesn't
        factory = TextWidgetBackend.get_backend(MFPGUI().appwin.backend_name)
        self.backend = factory(self)
