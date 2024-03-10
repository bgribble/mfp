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
    SDL_PollEvent,
    SDL_TEXTINPUT,
    SDL_QUIT,
    SDL_Quit,
)
import imgui
from imgui.integrations.sdl2 import SDL2Renderer
import OpenGL.GL as gl

from mfp import log
from mfp.gui_main import MFPGUI
from ..app_window import AppWindow, AppWindowImpl
from .utils import create_sdl2_window
from .inputs import imgui_process_inputs, imgui_key_map
from ..event import KeyPressEvent, KeyReleaseEvent, ButtonPressEvent, ButtonReleaseEvent


class ImguiAppWindowImpl(AppWindow, AppWindowImpl):
    backend_name = "imgui"
    INIT_WIDTH = 800
    INIT_HEIGHT = 600

    async def _render_task(self):
        keep_going = True
        event = SDL_Event()

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
                    ev = KeyPressEvent(
                        target=self.input_mgr.pointer_obj,
                        keyval=None,
                        unicode=event.text.text.decode('utf-8')
                    )
                    MFPGUI().async_task(self.signal_emit("key-press-event", ev))
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

        self.keymap = imgui_key_map()

        MFPGUI().async_task(self._render_task())

    def shutdown(self):
        log.debug("[imgui] shutdown")
        self.close_in_progress = True

    #####################
    # renderer
    def render(self):
        # process input state and convert to events
        imgui_process_inputs(self)

        # one window that fills the workspace
        imgui.set_next_window_size(self.window_width, self.window_height-21)
        imgui.set_next_window_position(0, 21)
        imgui.get_style().window_rounding = 0
        imgui.style_colors_light()

        imgui.begin(
            "mfp",
            closable=False,
            flags=imgui.WINDOW_NO_MOVE | imgui.WINDOW_ALWAYS_AUTO_RESIZE,
        )
        imgui.text("Hello, world!")

        imgui.end()

        return True

    def grab_focus(self):
        pass

    def ready(self):
        pass

    #####################
    # coordinate transforms and zoom

    def screen_to_canvas(self, x, y):
        pass

    def canvas_to_screen(self, x, y):
        pass

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
