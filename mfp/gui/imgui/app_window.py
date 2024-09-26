"""
imgui/app_window.py
Main window class for ImGui backend
"""

import asyncio
import sys
from datetime import datetime

from imgui_bundle import imgui, imgui_node_editor as nedit
# from imgui_bundle imgui_md as markdown
import OpenGL.GL as gl

from mfp import log
from mfp.gui_main import MFPGUI
from mfp.gui.connection_element import ConnectionElement
from mfp.gui.modes.patch_edit import PatchEditMode
from ..app_window import AppWindow, AppWindowImpl
from .inputs import imgui_process_inputs, imgui_key_map
from .sdl2_renderer import ImguiSDL2Renderer as ImguiRenderer
from ..event import EnterEvent, LeaveEvent
from . import info_panel, menu_bar

class ImguiAppWindowImpl(AppWindow, AppWindowImpl):
    backend_name = "imgui"
    motion_overrides = ["drag", "zoom", "canvas_pos"]

    INIT_WIDTH = 900
    INIT_HEIGHT = 700

    INIT_INFO_PANEL_WIDTH = 300
    INIT_CONSOLE_PANEL_HEIGHT = 150
    MENU_HEIGHT = 21

    def __init__(self, *args, **kwargs):
        self.imgui_impl = None
        self.imgui_renderer = None
        self.imgui_repeating_keys = {}

        self.info_panel_id = None
        self.info_panel_visible = True
        self.info_panel_width = self.INIT_INFO_PANEL_WIDTH

        self.console_panel_id = None
        self.console_panel_visible = True
        self.console_panel_height = self.INIT_CONSOLE_PANEL_HEIGHT

        self.canvas_panel_id = None
        self.canvas_panel_width = self.INIT_WIDTH - self.INIT_INFO_PANEL_WIDTH

        self.frame_count = 0
        self.frame_timestamps = []

        self.selected_window = "canvas"

        self.inspector = None

        self.log_text = ""

        self.user_zoom_set = False

        super().__init__(*args, **kwargs)

        self.signal_listen("motion-event", self.handle_motion)

    async def handle_motion(self, target, signal, event, *rest):
        prev_pointer_obj = event.target
        new_pointer_obj = prev_pointer_obj
        if self.console_panel_visible:
            if event.y >= self.window_height - self.console_panel_height:
                if prev_pointer_obj != self.console_manager:
                    new_pointer_obj = self.console_manager
        if not new_pointer_obj and self.info_panel_visible:
            if event.x < self.canvas_panel_width:
                new_pointer_obj = self
            else:
                new_pointer_obj = None
        if new_pointer_obj != prev_pointer_obj:
            if prev_pointer_obj:
                await self.signal_emit("leave-event", LeaveEvent(target=prev_pointer_obj))
            if new_pointer_obj != self:
                await self.signal_emit("enter-event", EnterEvent(target=new_pointer_obj))
        return False

    async def _render_task(self):
        keep_going = True

        io = imgui.get_io()
        io.config_flags |= imgui.ConfigFlags_.docking_enable
        io.config_input_trickle_event_queue = True
        io.config_input_text_cursor_blink = False

        # FIXME can't use imgui_md -- it depends on immmap
        # markdown.initialize_markdown()
        # font_loader = markdown.get_font_loader_function()
        # font_loader()

        config = nedit.Config()
        config.settings_file = "/dev/null"

        ed = nedit.create_editor(config)
        nedit.set_current_editor(ed)

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

        nedit.destroy_editor(ed)
        self.imgui_renderer.shutdown()
        self.imgui_impl.shutdown()
        await self.signal_emit("quit")

    #####################
    # backend control
    def initialize(self):
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
        from mfp.gui.modes.global_mode import GlobalMode
        from mfp.gui.modes.console_mode import ConsoleMode
        keep_going = True

        ########################################
        # global style setup
        imgui.style_colors_light()
        imgui.push_style_color(imgui.Col_.text_selected_bg, (200, 200, 255, 255))

        ########################################
        # menu bar
        if imgui.begin_main_menu_bar():
            quit_selected = menu_bar.render(self)
            if quit_selected:
                keep_going = False

            imgui.end_main_menu_bar()
        # menu bar
        ########################################

        ########################################
        # full-screen window containing the dockspace
        imgui.set_next_window_size((self.window_width, self.window_height - 2*self.MENU_HEIGHT))
        imgui.set_next_window_pos((0, self.MENU_HEIGHT))

        # main window is plain, no border, no padding
        imgui.push_style_var(imgui.StyleVar_.window_rounding, 0)
        imgui.push_style_var(imgui.StyleVar_.window_border_size, 0)
        imgui.push_style_var(imgui.StyleVar_.window_padding, (0, 0))

        imgui.begin(
            "main window content",
            flags=(
                imgui.WindowFlags_.no_collapse
                | imgui.WindowFlags_.no_move
                | imgui.WindowFlags_.no_docking
                | imgui.WindowFlags_.no_title_bar
                | imgui.WindowFlags_.no_resize
                | imgui.WindowFlags_.no_saved_settings
            ),
        )

        imgui.push_style_var(imgui.StyleVar_.window_border_size, 1)
        imgui.push_style_var(imgui.StyleVar_.window_padding, (1, 1))

        dockspace_id = imgui.get_id("main window dockspace")
        imgui.dock_space(
            dockspace_id,
            (0, 0),
            imgui.DockNodeFlags_.none
        )

        if self.frame_count == 0:
            imgui.internal.dock_builder_remove_node(dockspace_id)
            imgui.internal.dock_builder_add_node(
                dockspace_id,
                imgui.internal.DockNodeFlagsPrivate_.dock_space
            )
            imgui.internal.dock_builder_set_node_size(dockspace_id, imgui.get_window_size())

            _, self.console_panel_id, self.canvas_panel_id = (
                imgui.internal.dock_builder_split_node_py(
                    dockspace_id, imgui.Dir_.down, 0.30
                )
            )
            _, self.info_panel_id, self.canvas_panel_id = (
                imgui.internal.dock_builder_split_node_py(
                    self.canvas_panel_id, imgui.Dir_.right, 0.33
                )
            )

            node_flags = (
                imgui.internal.DockNodeFlagsPrivate_.no_close_button
                | imgui.internal.DockNodeFlagsPrivate_.no_window_menu_button
                | imgui.internal.DockNodeFlagsPrivate_.no_tab_bar
            )

            for node_id in [self.info_panel_id, self.console_panel_id, self.canvas_panel_id]:
                node = imgui.internal.dock_builder_get_node(node_id)
                node.local_flags = node_flags

            imgui.internal.dock_builder_dock_window("info_panel", self.info_panel_id)
            imgui.internal.dock_builder_dock_window("console_panel", self.console_panel_id)
            imgui.internal.dock_builder_dock_window("canvas", self.canvas_panel_id)
            imgui.internal.dock_builder_finish(dockspace_id)

        console_node = imgui.internal.dock_builder_get_node(self.console_panel_id)
        console_size = console_node.size
        self.console_panel_height = console_size[1]

        info_node = imgui.internal.dock_builder_get_node(self.info_panel_id)
        info_size = info_node.size
        self.info_panel_width = info_size[0]

        canvas_node = imgui.internal.dock_builder_get_node(self.canvas_panel_id)
        canvas_size = canvas_node.size

        ########################################
        # canvas window
        self.canvas_panel_width = canvas_width = canvas_size[0]
        canvas_height = canvas_size[1]
        canvas_x = 0
        if self.info_panel_visible:
            canvas_width -= self.info_panel_width
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
        if imgui.is_window_focused(imgui.FocusedFlags_.child_windows):
            self.selected_window = "canvas"
            if not isinstance(self.input_mgr.global_mode, GlobalMode):
                self.input_mgr.global_mode = GlobalMode(self)
                self.input_mgr.major_mode.enable()
        nedit.begin("canvas_editor", imgui.ImVec2(0.0, 0.0))

        conf = nedit.get_config()
        if isinstance(self.input_mgr.major_mode, PatchEditMode):
            conf.drag_button_index = 0
        else:
            conf.drag_button_index = 3

        actual_zoom = nedit.get_current_zoom()

        # FIXME +/-/0 binding keys don't work yet
        if self.user_zoom_set and actual_zoom != self.zoom:
            self.user_zoom_set = False
            self.zoom = actual_zoom
        elif not self.user_zoom_set and actual_zoom != self.zoom:
            self.zoom = actual_zoom

        # first pass: non-links
        all_pins = {}
        for obj in self.objects:
            if not isinstance(obj, ConnectionElement):
                obj.render()
                for port_id, pin_id in obj.port_elements.items():
                    all_pins[pin_id.id()] = (obj, port_id)

        # second pass: links
        for obj in self.objects:
            if isinstance(obj, ConnectionElement):
                obj.render()

        #############################
        # creation of links (by click-drag)
        if nedit.begin_create():
            start_pin = nedit.PinId.create()
            end_pin = nedit.PinId.create()
            if nedit.query_new_link(start_pin, end_pin):
                if start_pin and end_pin and nedit.accept_new_item():
                    start_obj, start_port_id = all_pins.get(start_pin.id(), (None, None))
                    end_obj, end_port_id = all_pins.get(end_pin.id(), (None, None))
                    log.debug(f"[window] connecting {start_obj} {start_port_id} to {end_obj} {end_port_id}")
                    MFPGUI().async_task(
                        self.render_make_connection(start_obj, start_port_id[1], end_obj, end_port_id[1])
                    )
            nedit.end_create()

        nedit.end()  # node_editor

        imgui.end()

        # canvas window
        ########################################

        ########################################
        # right-side info display
        if self.info_panel_visible:
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
            if imgui.is_window_focused(imgui.FocusedFlags_.child_windows):
                self.selected_window = "info"
            info_panel.render(self)
            imgui.end()

        # right-side info display
        ########################################

        ########################################
        # bottom panel (console and log)
        if self.console_panel_visible:
            imgui.begin(
                "console_panel",
                flags=(
                    imgui.WindowFlags_.no_collapse
                    | imgui.WindowFlags_.no_move
                    | imgui.WindowFlags_.no_title_bar
                ),
            )
            if imgui.is_window_focused(imgui.FocusedFlags_.child_windows):
                self.selected_window = "console"
                if not isinstance(self.input_mgr.global_mode, ConsoleMode):
                    self.input_mgr.global_mode = ConsoleMode(self)
                    self.input_mgr.major_mode.disable()
                    for m in list(self.input_mgr.minor_modes):
                        self.input_mgr.disable_minor_mode(m)

            if imgui.begin_tab_bar("console_tab_bar", imgui.TabBarFlags_.none):
                if imgui.begin_tab_item("Log")[0]:
                    imgui.input_text_multiline(
                        'log_output_text',
                        self.log_text,
                        (self.window_width, self.console_panel_height - self.MENU_HEIGHT),
                        imgui.InputTextFlags_.read_only
                    )
                    imgui.end_tab_item()
                if imgui.begin_tab_item("Console")[0]:
                    self.console_manager.render(self.window_width, self.console_panel_height - self.MENU_HEIGHT)
                    imgui.end_tab_item()
                imgui.end_tab_bar()

            imgui.end()

        # console
        ########################################

        imgui.pop_style_var()  # padding
        imgui.pop_style_var()  # border
        imgui.end()

        imgui.pop_style_var()  # padding
        imgui.pop_style_var()  # border
        imgui.pop_style_var()  # rounding

        imgui.pop_style_color() # text selected bg

        # full-screen window
        ########################################

        ########################################
        # status line at bottom
        imgui.set_next_window_size((self.window_width, self.MENU_HEIGHT))
        imgui.set_next_window_pos((0, self.window_height - self.MENU_HEIGHT))
        imgui.begin(
            "status_line",
            flags=(
                imgui.WindowFlags_.no_collapse
                | imgui.WindowFlags_.no_move
                | imgui.WindowFlags_.no_title_bar
                | imgui.WindowFlags_.no_decoration
            ),
        )

        if len(self.frame_timestamps) > 1:
            elapsed = (self.frame_timestamps[-1] - self.frame_timestamps[0]).total_seconds()
            imgui.text(f"FPS: {int((len(self.frame_timestamps)-1) / elapsed)}")

        imgui.end()

        # status line at bottom
        ########################################

        ########################################
        # flopsy inspector should be in an independent window

        if self.inspector is not None:
            inspector_keep_going = self.inspector.render()
            if not inspector_keep_going:
                self.inspector = None

        # process input state and convert to events
        imgui_process_inputs(self)

        # clean up any weirdness from first frame
        if self.frame_count == 0:
            self.selected_window = "canvas"

        self.frame_count += 1
        self.frame_timestamps.append(datetime.now())
        if len(self.frame_timestamps) > 10:
            self.frame_timestamps = self.frame_timestamps[-10:]
        return keep_going

    # helper for interactive connect-by-click
    async def render_make_connection(self, src_obj, src_port, dest_obj, dest_port):
        return await MFPGUI().mfp.connect(
            src_obj.obj_id,
            src_port,
            dest_obj.obj_id,
            dest_port
        )

    def grab_focus(self):
        pass

    def ready(self):
        pass

    def object_visible(self, obj):
        if obj and hasattr(obj, 'layer'):
            return obj.layer == self.selected_layer
        if obj == self.console_manager:
            return True
        return True

    #####################
    # coordinate transforms and zoom

    def screen_to_canvas(self, x, y):
        return nedit.screen_to_canvas((x, y))

    def canvas_to_screen(self, x, y):
        return nedit.canvas_to_screen((x, y))

    def rezoom(self):
        self.user_zoom_set = True

    def get_size(self):
        return (self.window_width, self.window_height)

    #####################
    # element operations
    def register(self, element):
        super().register(element)

    def unregister(self, element):
        super().unregister(element)

    def refresh(self, element):
        pass

    async def select(self, element):
        return await AppWindow.select(self, element)

    async def unselect(self, element):
       return await AppWindow.unselect(self, element)

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
        return []

    def hide_selection_box(self):
        pass

    #####################
    # log output
    def log_write(self, message, level):
        self.log_text = self.log_text + message

    #####################
    # key bindings display
    def display_bindings(self):
        pass
