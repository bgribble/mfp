"""
imgui/app_window.py
Main window class for ImGui backend
"""

import asyncio
import ctypes
import sys

from sdl2 import (
    SDL_DestroyWindow,
    SDL_Event,
    SDL_GL_SwapWindow,
    SDL_GL_DeleteContext,
    SDL_KEYDOWN,
    SDL_MOUSEWHEEL,
    SDL_MOUSEMOTION,
    SDL_PollEvent,
    SDL_TEXTINPUT,
    SDL_QUIT,
    SDL_Quit,
    SDL_SCANCODE_LCTRL, SDL_SCANCODE_RCTRL, SDL_SCANCODE_CAPSLOCK, SDL_SCANCODE_ESCAPE,
    SDLK_LCTRL, SDLK_RCTRL, SDLK_CAPSLOCK, SDLK_ESCAPE
)
from imgui_bundle import imgui
from imgui_bundle.python_backends.sdl_backend import SDL2Renderer
import OpenGL.GL as gl

from mfp import log
from mfp.gui_main import MFPGUI
from ..app_window import AppWindow, AppWindowImpl
from .utils import create_sdl2_window, update_sdl2_keymap
from .inputs import imgui_process_inputs, imgui_key_map
from ..event import KeyPressEvent, ScrollEvent, MotionEvent

# keys that are often remapped at the OS level. Check for these
# and manage them.
SDL_REMAPPABLE = {
    SDLK_LCTRL: (SDL_SCANCODE_LCTRL, imgui.Key.im_gui_mod_ctrl),
    SDLK_RCTRL: (SDL_SCANCODE_RCTRL, imgui.Key.im_gui_mod_ctrl),
    SDLK_CAPSLOCK: (SDL_SCANCODE_CAPSLOCK, None),
    SDLK_ESCAPE: (SDL_SCANCODE_ESCAPE, imgui.Key.escape),
}

class ImguiAppWindowImpl(AppWindow, AppWindowImpl):
    backend_name = "imgui"
    INIT_WIDTH = 800
    INIT_HEIGHT = 600

    async def _render_task(self):
        keep_going = True
        event = SDL_Event()

        io = imgui.get_io()
        io.config_input_trickle_event_queue = True

        while (
            keep_going
            and not self.close_in_progress
        ):
            await asyncio.sleep(0)
            while SDL_PollEvent(ctypes.byref(event)) != 0:
                await asyncio.sleep(0)
                if event.type == SDL_QUIT:
                    keep_going = False
                    break

                if event.type == SDL_TEXTINPUT:
                    # text-generating key presses don't "count" to imgui
                    # for some reason.
                    ev = KeyPressEvent(
                        target=self.input_mgr.pointer_obj,
                        keyval=None,
                        unicode=event.text.text.decode('utf-8')
                    )
                    MFPGUI().async_task(self.signal_emit("key-press-event", ev))
                elif event.type == SDL_KEYDOWN:
                    # imgui doesn't automatically remap keys, but we can
                    # do it live because SDL reports both the scancode and the
                    # keycode
                    if event.key.keysym.sym in SDL_REMAPPABLE:
                        remap_info = SDL_REMAPPABLE.get(event.key.keysym.sym)
                        if event.key.keysym.scancode != remap_info[0]:
                            if self.imgui_renderer.key_map.get(event.key.keysym.scancode) != remap_info[1]:
                                self.imgui_renderer.key_map[event.key.keysym.scancode] = remap_info[1]
                elif event.type == SDL_MOUSEWHEEL:
                    ev = ScrollEvent(
                        target=self.input_mgr.pointer_obj,
                        dx=event.wheel.x,
                        dy=event.wheel.y
                    )
                    MFPGUI().async_task(self.signal_emit("scroll-event", ev))
                elif event.type == SDL_MOUSEMOTION:
                    ev = MotionEvent(
                        target=self.input_mgr.pointer_obj,
                        x=event.motion.x,
                        y=event.motion.y
                    )
                    MFPGUI().async_task(self.signal_emit("motion-event", ev))

                self.imgui_renderer.process_event(event)

            # top of loop stuff
            self.imgui_renderer.process_inputs()

            # start processing for this frame
            imgui.new_frame()

            # hard work
            keep_going = self.render()

            # bottom of loop stuff
            gl.glClearColor(1.0, 1.0, 1.0, 1)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            imgui.render()
            self.imgui_renderer.render(imgui.get_draw_data())
            SDL_GL_SwapWindow(self.sdl2_window)

        self.imgui_renderer.shutdown()
        SDL_GL_DeleteContext(self.gl_context)
        SDL_DestroyWindow(self.sdl2_window)
        SDL_Quit()
        await self.signal_emit("quit")

    #####################
    # backend control
    def initialize(self):
        log.debug("[imgui] initialize")
        self.window_width = self.INIT_WIDTH
        self.window_height = self.INIT_HEIGHT
        self.icon_path = sys.exec_prefix + '/share/mfp/icons/'
        self.keys_pressed = set()
        self.buttons_pressed = set()

        # create the window and renderer
        self.sdl2_window, self.gl_context = create_sdl2_window(
            "mfp", self.window_width, self.window_height, self.icon_path
        )
        imgui.create_context()
        log.debug(f"[imgui] window={self.sdl2_window} context={self.gl_context}")
        self.imgui_renderer = SDL2Renderer(self.sdl2_window)

        update_sdl2_keymap(self.imgui_renderer)

        self.keymap = imgui_key_map()
        self.mouse_clicks = {}

        MFPGUI().async_task(self._render_task())

    def shutdown(self):
        log.debug("[imgui] shutdown")
        self.close_in_progress = True

    #####################
    # renderer
    def render(self):
        keep_going = True

        # process input state and convert to events
        imgui_process_inputs(self)

        ########################################
        # global menu bar
        if imgui.begin_main_menu_bar():
            if imgui.begin_menu("File"):
                # Quit
                clicked, rest = imgui.menu_item("Quit", "Ctrl+Q", False)
                if clicked:
                    keep_going = False
                imgui.end_menu()

            imgui.end_main_menu_bar()

        # one window that fills the workspace
        imgui.set_next_window_size((self.window_width, self.window_height-21))
        imgui.set_next_window_pos((0, 21))
        imgui.get_style().window_rounding = 0
        imgui.get_style().window_border_size = 0
        imgui.style_colors_light()

        imgui.begin(
            "mfp",
            flags=(
                imgui.WindowFlags_.no_collapse
                | imgui.WindowFlags_.no_move
                | imgui.WindowFlags_.always_auto_resize
                | imgui.WindowFlags_.no_title_bar
            ),
        )

        imgui.end()

        return keep_going

    def grab_focus(self):
        pass

    def ready(self):
        pass

    #####################
    # coordinate transforms and zoom

    def screen_to_canvas(self, x, y):
        return (x, y)

    def canvas_to_screen(self, x, y):
        return (x, y)

    def rezoom(self):
        pass

    def get_size(self):
        return (self.window_width, self.window_height)

    #####################
    # element operations

    def register(self, element):
        pass

    def unregister(self, element):
        pass

    def refresh(self, element):
        pass

    def select(self, element):
        pass

    def unselect(self, element):
        pass

    #####################
    # autoplace

    def show_autoplace_marker(self, x, y):
        pass

    def hide_autoplace_marker(self):
        pass

    #####################
    # HUD/console

    def hud_banner(self, message, display_time=3.0):
        pass

    def hud_write(self, message, display_time=3.0):
        pass

    def hud_set_prompt(self, prompt, default=''):
        pass

    def console_activate(self):
        pass

    #####################
    # clipboard
    def clipboard_get(self, pointer_pos):
        pass

    def clipboard_set(self, pointer_pos):
        pass

    def clipboard_cut(self, pointer_pos):
        pass

    def clipboard_copy(self, pointer_pos):
        pass

    def clipboard_paste(self, pointer_pos=None):
        pass

    #####################
    # selection box
    def show_selection_box(self, x0, y0, x1, y1):
        pass

    def hide_selection_box(self):
        pass

    #####################
    # log output
    def log_write(self, message, level):
        pass

    #####################
    # key bindings display
    def display_bindings(self):
        pass
