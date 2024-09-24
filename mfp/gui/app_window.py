#! /usr/bin/env python
'''
app_window.py
The main MFP window and associated code
'''


from abc import ABC, abstractmethod
from mfp import log

from mfp.utils import SignalMixin
from ..gui_main import MFPGUI
from .backend_interfaces import BackendInterface
from .input_manager import InputManager
from .layer import Layer
from .console_manager import ConsoleManager
from .prompter import Prompter
from .colordb import ColorDB, RGBAColor
from .base_element import BaseElement
from .modes.global_mode import GlobalMode
from .modes.patch_edit import PatchEditMode
from .modes.patch_control import PatchControlMode


class AppWindowImpl(BackendInterface, ABC):
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
    def grab_focus(self):
        pass

    @abstractmethod
    def ready(self):
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
    def rezoom(self):
        pass

    @abstractmethod
    def get_size(self):
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
    async def select(self, element):
        pass

    @abstractmethod
    async def unselect(self, element):
        pass

    #####################
    # autoplace

    @abstractmethod
    def show_autoplace_marker(self, x, y):
        pass

    @abstractmethod
    def hide_autoplace_marker(self):
        pass

    #####################
    # HUD/console

    @abstractmethod
    def hud_banner(self, message, display_time=3.0):
        pass

    @abstractmethod
    def hud_write(self, message, display_time=3.0):
        pass

    @abstractmethod
    def hud_set_prompt(self, prompt, default=''):
        pass

    @abstractmethod
    def console_activate(self):
        pass

    #####################
    # clipboard

    @abstractmethod
    def clipboard_get(self, pointer_pos):
        pass

    @abstractmethod
    def clipboard_set(self, pointer_pos):
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

    #####################
    # selection box

    @abstractmethod
    def show_selection_box(self, x0, y0, x1, y1):
        pass

    @abstractmethod
    def hide_selection_box(self):
        pass

    #####################
    # log output

    @abstractmethod
    def log_write(self, message, level):
        pass

    #####################
    # key bindings display

    @abstractmethod
    def display_bindings(self):
        pass


class AppWindow (SignalMixin):
    def __init__(self):
        super().__init__()

        # self.objects is BaseElement instances representing the
        # currently-displayed patch(es)
        self.patches = []
        self.objects = []
        self.object_counts_by_type = {}

        self.selected_patch = None
        self.selected_layer = None
        self.selected_window = "canvas"

        self.selected = []

        self.load_in_progress = 0
        self.close_in_progress = False

        # dumb colors
        self.color_unselected = self.get_color('stroke-color')
        self.color_transparent = ColorDB().find('transparent')
        self.color_selected = self.get_color('stroke-color:selected')
        self.color_bg = self.get_color('canvas-color')

        # viewport info
        self.zoom = 1.0
        self.view_x = 0
        self.view_y = 0

        # impl-specific mapping of widgets to MFP display elements
        self.event_sources = {}

        # set up key and mouse handling
        self.input_mgr = InputManager(self)
        self.init_input()

        self.hud_prompt_mgr = Prompter(self)

        self.initialize()

        self.console_manager = ConsoleManager.build("MFP interactive console", self)
        self.console_manager.start()


    @classmethod
    def get_backend(cls, backend_name):
        return AppWindowImpl.get_backend(backend_name)

    @classmethod
    def build(cls, *args, **kwargs):
        return cls.get_backend(MFPGUI().backend_name)(*args, **kwargs)

    def input_handler(self, target, signal, event, *rest):
        try:
            rv = self.input_mgr.handle_event(target, event)
            self.grab_focus()
            return rv
        except Exception as e:
            log.error("Error handling UI event", event)
            log.debug(e)
            log.debug_traceback()
            return False

    def init_input(self):
        # set initial major mode
        self.input_mgr.global_mode = GlobalMode(self)
        self.input_mgr.major_mode = PatchEditMode(self)
        self.input_mgr.major_mode.enable()

        # hook up input signals
        self.signal_listen('button-press-event', self.input_handler)
        self.signal_listen('button-release-event', self.input_handler)
        self.signal_listen('key-press-event', self.input_handler)
        self.signal_listen('key-release-event', self.input_handler)
        self.signal_listen('motion-event', self.input_handler)
        self.signal_listen('scroll-event', self.input_handler)
        self.signal_listen('enter-event', self.input_handler)
        self.signal_listen('leave-event', self.input_handler)
        self.signal_listen('quit', self.quit)

    def get_color(self, colorspec):
        from mfp.gui_main import MFPGUI
        rgba = MFPGUI().style_defaults.get(colorspec)
        if not rgba:
            return None
        elif isinstance(rgba, str):
            return ColorDB().find(rgba)
        elif isinstance(rgba, (list, tuple)):
            return ColorDB().find(rgba[0], rgba[1], rgba[2], rgba[3])
        else:
            return rgba

    def load_start(self):
        self.load_in_progress += 1

    def load_complete(self):
        self.load_in_progress -= 1
        if (self.load_in_progress <= 0):
            if self.selected_patch is None and len(self.patches):
                self.selected_patch = self.patches[0]
            if self.selected_layer is None and self.selected_patch is not None:
                self.layer_select(self.selected_patch.layers[0])

    def add_patch(self, patch_display):
        self.patches.append(patch_display)
        self.selected_patch = patch_display
        if len(patch_display.layers):
            self.layer_select(self.selected_patch.layers[0])

    def object_visible(self, obj):
        if obj and hasattr(obj, 'layer'):
            return obj.layer == self.selected_layer
        return True

    def active_layer(self):
        if self.selected_layer is None:
            if self.selected_patch is not None:
                self.layer_select(self.selected_patch.layers[0])

        return self.selected_layer

    def edit_major_mode(self):
        for o in self.selected:
            o.end_control()

        if isinstance(self.input_mgr.major_mode, PatchControlMode):
            self.input_mgr.set_major_mode(PatchEditMode(self))
        return True

    async def control_major_mode(self):
        for o in self.selected:
            await o.end_edit()
            o.begin_control()

        if isinstance(self.input_mgr.major_mode, PatchEditMode):
            self.input_mgr.set_major_mode(PatchControlMode(self))
        return True

    def register(self, element):
        self.objects.append(element)

        oldcount = self.object_counts_by_type.get(element.display_type, 0)
        self.object_counts_by_type[element.display_type] = oldcount + 1
        MFPGUI().async_task(self.signal_emit("add", element))

        if element.obj_id is not None:
            element.send_params()

    def unregister(self, element):
        if element in self.selected:
            MFPGUI().async_task(self.unselect(element))
        if element.layer:
            element.layer.remove(element)
        if element in self.objects:
            self.objects.remove(element)

        MFPGUI().async_task(self.signal_emit("remove", element))

    async def add_element(self, factory, x=None, y=None):
        if x is None:
            x = self.input_mgr.pointer_x
        if y is None:
            y = self.input_mgr.pointer_y

        try:
            b = factory(self, x, y)
        except Exception as e:
            log.warning("add_element: Error while creating with factory", factory)
            log.debug_traceback(e)
            return True

        self.active_layer().add(b)
        self.register(b)
        self.refresh(b)
        await self.select(b)
        await b.begin_edit()
        return True

    async def quit(self, *rest):
        from .patch_display import PatchDisplay
        log.debug("quit: received command from GUI or WM")

        self.close_in_progress = True
        try:
            to_delete = [p for p in self.patches if p.deletable]
            for p in to_delete:
                await p.delete()
            allpatches = await MFPGUI().mfp.open_patches()
            guipatches = [p.obj_id for p in self.objects if isinstance(p, PatchDisplay)]
        except Exception as e:
            log.debug(f"Error while quitting: {e}")
            raise
        for a in allpatches:
            if a not in guipatches:
                log.debug("Some patches cannot be deleted, not quitting")
                log.debug(f"{allpatches} {guipatches}")
                return False

        if hasattr(self, 'console_manager') and self.console_manager:
            self.console_manager.finish()

        await MFPGUI().mfp.quit()
        self.close_in_progress = False
        log.debug("quit: shutdown complete")
        return True

    def console_write(self, msg):
        self.console_manager.append(msg)

    def console_show_prompt(self, msg):
        self.console_manager.show_prompt(msg)
        self.console_activate()

    async def get_prompted_input(self, prompt, callback, default=''):
        await self.hud_prompt_mgr.get_input(prompt, callback, default)

# additional methods in @extends wrappers
from . import app_window_layer  # noqa
from . import app_window_views  # noqa
from . import app_window_select  # noqa
