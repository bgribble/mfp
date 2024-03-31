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

    INIT_LEFT_PANEL_WIDTH = 150
    INIT_CONSOLE_PANEL_HEIGHT = 150
    MENU_HEIGHT = 21

    def __init__(self, *args, **kwargs):
        self.imgui_impl = None
        self.imgui_renderer = None

        self.left_panel_visible = True
        self.left_panel_width = self.INIT_LEFT_PANEL_WIDTH

        self.console_panel_visible = True
        self.console_panel_height = self.INIT_CONSOLE_PANEL_HEIGHT

        self.first_render = True
        super().__init__(*args, **kwargs)

    async def _render_task(self):
        keep_going = True

        io = imgui.get_io()
        io.config_flags |= imgui.ConfigFlags_.docking_enable
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
        # global style setup
        imgui.get_style().window_rounding = 0
        imgui.get_style().window_border_size = 1
        imgui.style_colors_light()

        ########################################
        # menu bar
        if imgui.begin_main_menu_bar():
            if imgui.begin_menu("File"):
                # Quit
                clicked, _ = imgui.menu_item("Quit", "Ctrl+Q", False)
                if clicked:
                    keep_going = False
                imgui.end_menu()

            imgui.end_main_menu_bar()


        ########################################
        # full-screen window containing the dockspace
        imgui.set_next_window_size((self.window_width, self.window_height - self.MENU_HEIGHT))
        imgui.set_next_window_pos((0, self.MENU_HEIGHT))

        imgui.begin(
            "main window content",
            flags=(
                imgui.WindowFlags_.no_collapse
                | imgui.WindowFlags_.no_move
                | imgui.WindowFlags_.no_docking
                | imgui.WindowFlags_.no_title_bar
                | imgui.WindowFlags_.no_resize
            ),
        )

        dockspace_id = imgui.get_id("main window dockspace")
        imgui.dock_space(
            dockspace_id,
            (0, 0),
            imgui.DockNodeFlags_.none
        )

        if self.first_render:
            self.first_render = False

            imgui.internal.dock_builder_remove_node(dockspace_id)
            imgui.internal.dock_builder_add_node(
                dockspace_id,
                imgui.internal.DockNodeFlagsPrivate_.dock_space
            )
            imgui.internal.dock_builder_set_node_size(dockspace_id, imgui.get_window_size())

            _, console_split_id, canvas_split_id = imgui.internal.dock_builder_split_node_py(
                dockspace_id, int(imgui.Dir_.down), 0.25
            )
            _, canvas_split_id, tree_split_id  = imgui.internal.dock_builder_split_node_py(
                canvas_split_id, int(imgui.Dir_.right), 0.75
            )
            
            node_flags = (
                imgui.internal.DockNodeFlagsPrivate_.no_close_button
                | imgui.internal.DockNodeFlagsPrivate_.no_window_menu_button
                | imgui.internal.DockNodeFlagsPrivate_.no_tab_bar
            )

            for node_id in [tree_split_id, console_split_id, canvas_split_id]:
                node = imgui.internal.dock_builder_get_node(node_id)
                node.local_flags = node_flags

            imgui.internal.dock_builder_dock_window("info_panel", tree_split_id)
            imgui.internal.dock_builder_dock_window("console_panel", console_split_id)
            imgui.internal.dock_builder_dock_window("canvas", canvas_split_id)
            imgui.internal.dock_builder_finish(dockspace_id)


        ########################################
        # left-side info display
        if self.left_panel_visible:
            panel_height = self.window_height - self.MENU_HEIGHT
            if self.console_panel_visible:
                panel_height -= self.console_panel_height

            imgui.begin(
                "info_panel",
                flags=(
                    imgui.WindowFlags_.no_collapse
                    | imgui.WindowFlags_.no_move
                    | imgui.WindowFlags_.no_title_bar
                ),
            )
            imgui.text("info panel")

            imgui.end()

        # left-side info display
        ########################################

        ########################################
        # canvas window
        canvas_width = self.window_width
        canvas_height = self.window_height - self.MENU_HEIGHT
        canvas_x = 0
        if self.left_panel_visible:
            canvas_width -= self.left_panel_width
            canvas_x += self.left_panel_width
        if self.console_panel_visible:
            canvas_height -= self.console_panel_height

        imgui.begin(
            "canvas",
            flags=(
                imgui.WindowFlags_.no_collapse
                | imgui.WindowFlags_.no_move
                | imgui.WindowFlags_.no_title_bar
            ),
        )
        imgui.text("canvas panel")

        imgui.end()

        # canvas window
        ########################################

        ########################################
        # console
        if self.console_panel_visible:
            imgui.begin(
                "console_panel",
                flags=(
                    imgui.WindowFlags_.no_collapse
                    | imgui.WindowFlags_.no_move
                    | imgui.WindowFlags_.no_title_bar
                ),
            )
            imgui.text("console panel")
            imgui.end()

        # console
        ########################################

        imgui.end()
        # full-screen window
        ########################################

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
