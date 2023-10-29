#! /usr/bin/env python
'''
app_window.py
The main MFP window and associated code
'''


from mfp import log

from mfp.utils import SignalMixin
from ..gui_main import MFPGUI
from .backend_interfaces import AppWindowBackend
from .input_manager import InputManager
from .console_manager import ConsoleManager
from .prompter import Prompter
from .colordb import ColorDB
from .modes.global_mode import GlobalMode
from .modes.patch_edit import PatchEditMode
from .modes.patch_control import PatchControlMode


class AppWindow (SignalMixin):
    backend_name = None

    def __init__(self):
        super().__init__()

        # self.objects is BaseElement instances representing the
        # currently-displayed patch(es)
        self.patches = []
        self.objects = []
        self.object_counts_by_type = {}

        self.selected_patch = None
        self.selected_layer = None
        self.selected = []

        self.load_in_progress = 0
        self.close_in_progress = False

        # dumb colors
        self.color_unselected = self.get_color('stroke-color')
        self.color_transparent = ColorDB().find('transparent')
        self.color_selected = self.get_color('stroke-color:selected')
        self.color_bg = self.get_color('canvas-color')

        # callbacks facility... not yet too much used, but "select" and
        # "add" are in use
        self.callbacks = {}
        self.callbacks_last_id = 0

        # viewport info
        self.zoom = 1.0
        self.view_x = 0
        self.view_y = 0

        # set up key and mouse handling
        self.input_mgr = InputManager(self)
        self.init_input()

        factory = AppWindowBackend.get_backend(AppWindow.backend_name)
        self.backend = factory(self)
        self.hud_prompt_mgr = Prompter(self)

        self.backend.initialize()

        self.console_manager = ConsoleManager("MFP interactive console", self)
        self.console_manager.start()

    def init_input(self):
        # set initial major mode
        self.input_mgr.global_mode = GlobalMode(self)
        self.input_mgr.major_mode = PatchEditMode(self)
        self.input_mgr.major_mode.enable()

    def get_color(self, colorspec):
        from mfp.gui_main import MFPGUI
        rgba = MFPGUI().style_defaults.get(colorspec)
        if not rgba:
            return None
        elif isinstance(rgba, str):
            return ColorDB().find(rgba)
        else:
            return ColorDB().find(rgba[0], rgba[1], rgba[2], rgba[3])

    def load_start(self):
        self.load_in_progress += 1

    def load_complete(self):
        self.load_in_progress -= 1
        if (self.load_in_progress <= 0):
            if self.selected_patch is None and len(self.patches):
                self.selected_patch = self.patches[0]
            if self.selected_layer is None and self.selected_patch is not None:
                self.layer_select(self.selected_patch.layers[0])
            self.backend.load_complete()

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

    def active_group(self):
        return self.active_layer().group

    def ready(self):
        if self.window and self.window.get_realized():
            return True
        else:
            return False

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
        self.input_mgr.event_sources[element] = element

        if element.obj_id is not None:
            element.send_params()

        self.backend.register(element)
        MFPGUI().async_task(self.signal_emit("add", element))

    def unregister(self, element):
        if element in self.selected:
            MFPGUI().async_task(self.unselect(element))
        if element.layer:
            element.layer.remove(element)
        if element in self.objects:
            self.objects.remove(element)
        if element in self.input_mgr.event_sources:
            del self.input_mgr.event_sources[element]

        self.backend.unregister(element)
        MFPGUI().async_task(self.signal_emit("remove", element))

    def refresh(self, element):
        self.backend.refresh(element)

    async def add_element(self, factory, x=None, y=None):
        if x is None:
            x = self.input_mgr.pointer_x
        if y is None:
            y = self.input_mgr.pointer_y

        try:
            b = factory(self.backend, x, y)
        except Exception as e:
            log.warning("add_element: Error while creating with factory", factory)
            log.warning(e)
            log.debug_traceback()
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

    def get_prompted_input(self, prompt, callback, default=''):
        self.hud_prompt_mgr.get_input(prompt, callback, default)

# additional methods in @extends wrappers
from . import app_window_layer  # noqa
from . import app_window_views  # noqa
from . import app_window_select  # noqa
