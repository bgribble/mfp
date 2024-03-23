"""
imgui/app_window.py
Main window class for ImGui backend
"""

import asyncio
import sys

from imgui_bundle import imgui
import OpenGL.GL as gl

from mfp import log
from mfp.gui_main import MFPGUI
from ..app_window import AppWindow, AppWindowImpl
from .inputs import imgui_process_inputs, imgui_key_map
from .sdl2_renderer import ImguiSDL2Renderer as ImguiRenderer


class ImguiAppWindowImpl(AppWindow, AppWindowImpl):
    backend_name = "imgui"
    INIT_WIDTH = 800
    INIT_HEIGHT = 600

    def __init__(self, *args, **kwargs):
        self.imgui_impl = None
        self.imgui_renderer = None

        super().__init__(*args, **kwargs)

    async def _render_task(self):
        keep_going = True

        io = imgui.get_io()
        io.config_input_trickle_event_queue = True

        while (
            keep_going
            and not self.close_in_progress
        ):
            # top of loop stuff
            await asyncio.sleep(0)
            await self.imgui_impl.process_events()
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

            self.imgui_impl.swap_window()

        self.imgui_renderer.shutdown()
        self.imgui_impl.shutdown()
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
        imgui.create_context()
        self.imgui_impl = ImguiRenderer(self)

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
                clicked, _ = imgui.menu_item("Quit", "Ctrl+Q", False)
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
