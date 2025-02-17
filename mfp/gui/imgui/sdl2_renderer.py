"""
Wrapper for Imgui backend-specific code for SDL2 backend

This will let me use different Imgui backends (GLFW,
SDL2, etc) without a lot of code changes. I know this is
basically the same as the "backend" concept I am already
using for clutter vs imgui but I am too tired to implement it
in a nice orthogonal way.
"""

# flake8: noqa: F405

import asyncio
import ctypes
import os

from sdl2 import *  # noqa
from imgui_bundle import imgui
from imgui_bundle.python_backends.sdl_backend import SDL2Renderer

from mfp.gui_main import MFPGUI
from mfp import log as mfplog
from ..event import KeyPressEvent, ScrollEvent, MotionEvent

# keys that are often remapped at the OS level. Check for these
# and manage them.
SDL_REMAPPABLE = {
    SDLK_LCTRL: (SDL_SCANCODE_LCTRL, imgui.Key.mod_ctrl),
    SDLK_RCTRL: (SDL_SCANCODE_RCTRL, imgui.Key.mod_ctrl),
    SDLK_CAPSLOCK: (SDL_SCANCODE_CAPSLOCK, None),
    SDLK_ESCAPE: (SDL_SCANCODE_ESCAPE, imgui.Key.escape),
}


class ImguiSDL2Renderer:
    def __init__(self, app_window):
        self.app_window = app_window

        self.window, self.gl_context = self.create_sdl2_window(
            "mfp", app_window.window_width, app_window.window_height, app_window.icon_path
        )
        self.renderer = SDL2Renderer(self.window)
        self.app_window.imgui_renderer = self.renderer
        self.update_sdl2_keymap()

    def update_sdl2_keymap(self):
        renderer = self.renderer
        renderer.key_map[SDL_SCANCODE_0] = imgui.Key(536)

        for index, _ in enumerate("123456789"):
            renderer.key_map[SDL_SCANCODE_1 + index] = imgui.Key(index + 537)

        for index, _ in enumerate("abcdefghijklmnopqrstuvwxyz"):
            renderer.key_map[SDL_SCANCODE_A + index] = imgui.Key(index + 546)

        renderer.key_map[SDL_SCANCODE_APOSTROPHE] = imgui.Key(596)
        renderer.key_map[SDL_SCANCODE_COMMA] = imgui.Key(597)
        renderer.key_map[SDL_SCANCODE_MINUS] = imgui.Key(598)
        renderer.key_map[SDL_SCANCODE_PERIOD] = imgui.Key(599)
        renderer.key_map[SDL_SCANCODE_SLASH] = imgui.Key(600)
        renderer.key_map[SDL_SCANCODE_SEMICOLON] = imgui.Key(601)
        renderer.key_map[SDL_SCANCODE_EQUALS] = imgui.Key(602)
        renderer.key_map[SDL_SCANCODE_LEFTBRACKET] = imgui.Key(603)
        renderer.key_map[SDL_SCANCODE_BACKSLASH] = imgui.Key(604)
        renderer.key_map[SDL_SCANCODE_RIGHTBRACKET] = imgui.Key(605)
        renderer.key_map[SDL_SCANCODE_GRAVE] = imgui.Key(606)

        # Fn keys
        for index in range(12):
            renderer.key_map[SDL_SCANCODE_F1 + index] = imgui.Key(572 + index)

    def create_sdl2_window(self, name, width, height, icon_path):
        os.environ['SDL_VIDEO_X11_WMCLASS'] = "com.billgribble.mfp"

        if SDL_Init(SDL_INIT_EVERYTHING) < 0:
            mfplog.error(
                "[sdl2] Error: SDL could not initialize! SDL Error: "
                + SDL_GetError().decode("utf-8")
            )
            return None, None

        SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1)
        SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24)
        SDL_GL_SetAttribute(SDL_GL_STENCIL_SIZE, 8)
        SDL_GL_SetAttribute(SDL_GL_ACCELERATED_VISUAL, 1)
        SDL_GL_SetAttribute(SDL_GL_MULTISAMPLEBUFFERS, 1)
        SDL_GL_SetAttribute(SDL_GL_MULTISAMPLESAMPLES, 8)
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_FLAGS, SDL_GL_CONTEXT_FORWARD_COMPATIBLE_FLAG)
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 4)
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1)
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_CORE)

        SDL_SetHint(SDL_HINT_MAC_CTRL_CLICK_EMULATE_RIGHT_CLICK, b"1")
        SDL_SetHint(SDL_HINT_VIDEO_HIGHDPI_DISABLED, b"1")
        SDL_SetHint(SDL_HINT_VIDEODRIVER, b"wayland,x11")
        SDL_SetHint(SDL_HINT_VIDEO_X11_FORCE_EGL, b"1")
        SDL_SetHint(SDL_HINT_APP_NAME, name.encode('utf-8'))

        window = SDL_CreateWindow(
            name.encode("utf-8"),
            SDL_WINDOWPOS_CENTERED,
            SDL_WINDOWPOS_CENTERED,
            width,
            height,
            SDL_WINDOW_OPENGL | SDL_WINDOW_RESIZABLE,
        )

        if window is None:
            mfplog.error(
                "[sdl2] Error: Window could not be created! SDL Error: "
                + SDL_GetError().decode("utf-8")
            )
            return None, None

        gl_context = SDL_GL_CreateContext(window)
        if gl_context is None:
            mfplog.error(
                "[sdl2] Error: Cannot create OpenGL Context! SDL Error: "
                + SDL_GetError().decode("utf-8")
            )
            return None, None

        SDL_GL_MakeCurrent(window, gl_context)
        if SDL_GL_SetSwapInterval(1) < 0:
            mfplog.error(
                "[sdl2] Error: Unable to set VSync! SDL Error: " + SDL_GetError().decode("utf-8")
            )
            return None, None
        mfplog.debug(f"[sdl2] Created window={window} context={gl_context}")
        return window, gl_context

    def swap_window(self):
        SDL_GL_SwapWindow(self.window)

    def shutdown(self):
        SDL_GL_DeleteContext(self.gl_context)
        SDL_DestroyWindow(self.window)
        SDL_Quit()

    async def process_events(self) -> bool:
        event = SDL_Event()
        width = ctypes.c_int()
        height = ctypes.c_int()
        events_processed = False
        unhandled_windows = ["info", "editor"]

        while SDL_PollEvent(ctypes.byref(event)) != 0:
            events_processed = True
            SDL_GetWindowSize(self.window, width, height)
            w_width = int(width.value)
            w_height = int(height.value)
            if w_width != self.app_window.window_width or w_height != self.app_window.window_height:
                self.app_window.window_width = w_width
                self.app_window.window_height = w_height

            if event.type == SDL_QUIT:
                return False, events_processed

            skip_event = False
            if event.type == SDL_TEXTINPUT:
                # text-generating key presses don't "count" to imgui
                # for some reason.
                ev = KeyPressEvent(
                    target=self.app_window.input_mgr.pointer_obj,
                    keyval=None,
                    unicode=event.text.text.decode('utf-8')
                )
                if self.app_window.selected_window not in unhandled_windows:
                    MFPGUI().async_task(self.app_window.signal_emit("key-press-event", ev))
            elif event.type == SDL_KEYDOWN:
                # for some reason SDL forces ALT-v to be ALT-INSERT
                if event.key.keysym.scancode == SDL_SCANCODE_INSERT and event.key.keysym.mod & KMOD_ALT:
                    ev = KeyPressEvent(
                        target=self.app_window.input_mgr.pointer_obj,
                        keyval=None,
                        unicode="v"
                    )
                    if self.app_window.selected_window not in unhandled_windows:
                        MFPGUI().async_task(self.app_window.signal_emit("key-press-event", ev))
                    skip_event = True

                # imgui doesn't automatically remap keys, but we can
                # do it live because SDL reports both the scancode and the
                # keycode
                if event.key.keysym.sym in SDL_REMAPPABLE:
                    remap_info = SDL_REMAPPABLE.get(event.key.keysym.sym)
                    if event.key.keysym.scancode != remap_info[0]:
                        if self.renderer.key_map.get(event.key.keysym.scancode) != remap_info[1]:
                            self.renderer.key_map[event.key.keysym.scancode] = remap_info[1]
            elif event.type == SDL_MOUSEWHEEL:
                ev = ScrollEvent(
                    target=self.app_window.input_mgr.pointer_obj,
                    dx=event.wheel.x,
                    dy=event.wheel.y
                )
                MFPGUI().async_task(self.app_window.signal_emit("scroll-event", ev))
            elif event.type == SDL_MOUSEMOTION:
                ev = MotionEvent(
                    target=self.app_window.input_mgr.pointer_obj,
                    x=event.motion.x,
                    y=event.motion.y
                )
                MFPGUI().async_task(self.app_window.signal_emit("motion-event", ev))

            if not skip_event:
                self.renderer.process_event(event)
            await asyncio.sleep(0)

        return True, events_processed
