"""
imgui/app_window.py
Main window class for ImGui backend
"""

import asyncio
import sys
from datetime import datetime, timedelta
from flopsy import Store

from imgui_bundle import imgui, imgui_node_editor as nedit
# from imgui_bundle imgui_md as markdown
import OpenGL.GL as gl

from mfp import log
from mfp.gui_main import MFPGUI
from mfp.gui.event import EnterEvent, LeaveEvent
from mfp.gui.app_window import AppWindow, AppWindowImpl
from mfp.gui.patch_display import PatchDisplay
from mfp.gui.tile_manager import TileManager, Tile
from ..inputs import imgui_process_inputs, imgui_key_map
from ..sdl2_renderer import ImguiSDL2Renderer as ImguiRenderer
from . import menu_bar, canvas_panel, info_panel, console_panel, status_line

MAX_RENDER_US = 200000
PEAK_FPS = 60


class ImguiAppWindowImpl(AppWindow, AppWindowImpl):
    backend_name = "imgui"
    motion_overrides = ["drag", "scroll-zoom", "canvas-pos"]

    INIT_WIDTH = 1200
    INIT_HEIGHT = 900

    INIT_INFO_PANEL_WIDTH = 350
    INIT_CONSOLE_PANEL_HEIGHT = 150
    INIT_MENU_HEIGHT = 21

    def __init__(self, *args, **kwargs):
        self.imgui_impl = None
        self.imgui_renderer = None
        self.imgui_repeating_keys = {}
        self.imgui_needs_reselect = []
        self.imgui_prevent_idle = False

        self.nedit_config = None

        self.menu_height = self.INIT_MENU_HEIGHT
        self.context_menu_open = False
        self.main_menu_open = False

        self.info_panel_id = None
        self.info_panel_visible = True
        self.info_panel_width = self.INIT_INFO_PANEL_WIDTH

        self.console_panel_id = None
        self.console_panel_visible = True
        self.console_panel_height = self.INIT_CONSOLE_PANEL_HEIGHT

        self.canvas_panel_id = None
        self.canvas_panel_width = self.INIT_WIDTH - self.INIT_INFO_PANEL_WIDTH
        self.canvas_panel_height = self.INIT_HEIGHT - self.INIT_CONSOLE_PANEL_HEIGHT

        self.canvas_tile_page = 0
        self.canvas_tile_manager = TileManager(
            self.canvas_panel_width,
            self.canvas_panel_height
        )

        self.autoplace_x = None
        self.autoplace_y = None

        self.frame_count = 0
        self.frame_timestamps = []
        self.viewport_box_nodes = None

        self.selected_window = "canvas"
        self.inspector = None

        self.log_text = ""

        super().__init__(*args, **kwargs)

        self.signal_listen("motion-event", self.handle_motion)
        self.signal_listen("toggle-console", self.handle_toggle_console)
        self.signal_listen("toggle-info-panel", self.handle_toggle_info_panel)

    async def handle_motion(self, target, signal, event, *rest):
        """
        Listener to set the currently-active panel based on pointer position
        """
        prev_pointer_obj = event.target
        new_pointer_obj = prev_pointer_obj
        if event.y < self.menu_height and self.selected_window != "menu":
            self.selected_window = "menu"
            new_pointer_obj = None

        if self.console_panel_visible:
            if event.y >= self.window_height - self.console_panel_height:
                if prev_pointer_obj != self.console_manager:
                    new_pointer_obj = self.console_manager
                    self.selected_window = "console"
        if not new_pointer_obj and self.info_panel_visible:
            if event.y > self.menu_height and event.x < self.canvas_panel_width:
                new_pointer_obj = self
        if new_pointer_obj != prev_pointer_obj:
            if prev_pointer_obj:
                await self.signal_emit("leave-event", LeaveEvent(target=prev_pointer_obj))
            if new_pointer_obj != self:
                await self.signal_emit("enter-event", EnterEvent(target=new_pointer_obj))
        return False

    async def handle_toggle_console(self, *rest):
        self.console_panel_visible = not self.console_panel_visible

    async def handle_toggle_info_panel(self, *rest):
        self.info_panel_visible = not self.info_panel_visible

    async def _render_task(self):
        keep_going = True
        next_frame_latest_delay = 10000

        io = imgui.get_io()
        io.config_flags |= imgui.ConfigFlags_.docking_enable
        io.config_input_trickle_event_queue = True
        io.config_input_text_cursor_blink = False

        # FIXME can't use imgui_md -- it depends on immmap
        # markdown.initialize_markdown()
        # font_loader = markdown.get_font_loader_function()
        # font_loader()

        self.nedit_config = nedit.Config()
        self.nedit_config.settings_file = "/dev/null"

        # FIXME this dummy editor is needed for some
        # hidden call to nedit.* during initialization of the
        # first patch. should be removed.
        nedit_editor = nedit.create_editor(self.nedit_config)
        nedit.set_current_editor(nedit_editor)

        gl.glClearColor(1.0, 1.0, 1.0, 1)

        sync_time = None
        while (
            keep_going
            and not self.close_in_progress
        ):
            # idle while there are no input events
            loop_start_time = datetime.now()

            while True:
                keep_going, events_processed = await self.imgui_impl.process_events()
                if datetime.now() > loop_start_time + timedelta(microseconds=next_frame_latest_delay):
                    next_frame_latest_delay = (next_frame_latest_delay + MAX_RENDER_US) / 2.0
                    break
                if events_processed or not keep_going:
                    next_frame_latest_delay = 10000
                    break
                if Store.last_activity_time() > loop_start_time:
                    next_frame_latest_delay = 10000
                    break
                if self.last_activity_time and self.last_activity_time > loop_start_time:
                    next_frame_latest_delay = 10000
                    break
                if self.imgui_prevent_idle:
                    break
                await asyncio.sleep(0.01)

            self.imgui_renderer.process_inputs()

            if not keep_going:
                continue

            # start processing for this frame
            imgui.new_frame()

            # hard work
            keep_going = self.render()

            ######################
            # bottom of loop stuff - hand over the frame to imgui

            if sync_time:
                # it seems like we are capped at 60 FPS and the sync happens
                # (blocking) in glClear(). If we do an asyncio sleep here, we can do
                # other work until the sync rolls around so glClear doesn't block
                elapsed_ms = (datetime.now() - sync_time).total_seconds() * 1000
                min_frame_ms = (1 / PEAK_FPS) * 1000
                if min_frame_ms > (elapsed_ms + 1):
                    sleepy_time = (min_frame_ms - elapsed_ms) / 1000
                    await asyncio.sleep(sleepy_time)

            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            sync_time = datetime.now()
            imgui.render()
            self.imgui_renderer.render(imgui.get_draw_data())
            self.imgui_impl.swap_window()

        for p in self.patches:
            if hasattr(p, 'nedit_editor'):
                nedit.destroy_editor(p.nedit_editor)
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
        self.close_in_progress = True

    #####################
    # renderer
    def render(self):
        self.imgui_prevent_idle = False
        keep_going = True

        ########################################
        # global style setup
        imgui.style_colors_classic()
        imgui.push_style_color(imgui.Col_.text_selected_bg, (200, 200, 255, 255))

        nedit.push_style_color(nedit.StyleColor.flow_marker, (1, 1, 1, 0.2))
        nedit.push_style_color(nedit.StyleColor.flow, (1, 1, 1, 0.5))

        ########################################
        # menu bar
        if imgui.begin_main_menu_bar():
            quit_selected = menu_bar.render(self)
            if quit_selected:
                keep_going = False

            imgui.end_main_menu_bar()

            _, menu_height = imgui.get_cursor_pos()
            self.menu_height = menu_height - 5
        # menu bar
        ########################################

        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0, 0))

        ########################################
        # full-screen window containing the dockspace
        imgui.set_next_window_size((self.window_width, self.window_height - 2*self.menu_height - 5))
        imgui.set_next_window_pos((0, self.menu_height))

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
                | imgui.WindowFlags_.no_bring_to_front_on_focus
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
                    dockspace_id, imgui.Dir_.down, 0.20
                )
            )
            _, self.info_panel_id, self.canvas_panel_id = (
                imgui.internal.dock_builder_split_node_py(
                    self.canvas_panel_id, imgui.Dir_.right, 0.30
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
        self.canvas_panel_width = canvas_size[0]
        self.canvas_panel_height = canvas_size[1]
        self.canvas_tile_manager.resize(canvas_size[0], canvas_size[1])

        ########################################
        # canvas panel
        canvas_panel.render(self)

        # canvas panel
        ########################################

        ########################################
        # right-side info display
        if self.info_panel_visible:
            info_panel.render(self)

        # right-side info display
        ########################################

        ########################################
        # bottom panel (console and log)
        if self.console_panel_visible:
            console_panel.render(self)

        # bottom panel
        ########################################


        imgui.pop_style_var()  # padding
        imgui.pop_style_var()  # border
        imgui.end()

        imgui.pop_style_var()  # padding
        imgui.pop_style_var()  # border
        imgui.pop_style_var()  # rounding
        imgui.pop_style_var()  # spacing

        imgui.pop_style_color()  # text selected bg
        nedit.pop_style_color(2)

        # full-screen window
        ########################################

        ########################################
        # status line and command input at bottom
        status_line.render(self)

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
        if not self.selected_patch or not self.selected_patch.display_info:
            return (x, y)
        di = self.selected_patch.display_info
        screen_x_delta = x - di.origin_x
        screen_y_delta = y - di.origin_y - self.menu_height - 20
        canvas_x = di.view_x + screen_x_delta / di.view_zoom
        canvas_y = di.view_y + screen_y_delta / di.view_zoom
        return (canvas_x, canvas_y)

    def canvas_to_screen(self, x, y):
        return nedit.canvas_to_screen((x, y))

    def move_view(self, dx, dy):
        patch = self.selected_patch

        patch.display_info.view_x -= dx / patch.display_info.view_zoom
        patch.display_info.view_y -= dy / patch.display_info.view_zoom
        self.viewport_pos_set = True
        return True

    def rezoom(self, **kwargs):
        patch = self.selected_patch
        if 'previous' in kwargs:
            prev_zoom = kwargs['previous']
            curr_zoom = patch.display_info.view_zoom

        self.viewport_zoom_set = True

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
        self.autoplace_x = x
        self.autoplace_y = y

    def hide_autoplace_marker(self):
        self.autoplace_x = None
        self.autoplace_y = None

    #####################
    # HUD/console

    def hud_banner(self, message, display_time=3.0):
        pass

    def hud_write(self, message, display_time=3.0):
        pass

    def cmd_set_prompt(self, prompt, default='', space=True):
        self.cmd_prompt = prompt
        if space and prompt:
            self.cmd_prompt += ' '

    def console_activate(self):
        pass

    #####################
    # clipboard
    def clipboard_get(self):
        return imgui.get_clipboard_text()

    def clipboard_set(self, cliptext):
        return imgui.set_clipboard_text(cliptext)

    #####################
    # selection box
    def show_selection_box(self, x0, y0, x1, y1):
        return []

    def hide_selection_box(self):
        pass

    #####################
    # layers
    def layer_create(self, layer, patch):
        pass

    def layer_update(self, layer, patch):
        pass

    #####################
    # patches / MDI
    def add_patch(self, patch):
        if isinstance(patch.display_info, Tile):
            patch.display_info.in_use = True
            self.canvas_tile_manager.add_tile(patch.display_info)
        else:
            tile = self.canvas_tile_manager.find_tile(page_id=self.canvas_tile_page)
            tile.in_use = True
            patch.display_info = tile
        self.viewport_zoom_set = True
        self.viewport_pos_set = True
        super().add_patch(patch)

    async def patch_close(self, patch=None):
        if patch is None:
            patch = self.selected_patch
        self.canvas_tile_manager.remove_tile(patch.display_info)
        return await super().patch_close(patch)

    #####################
    # log output
    def log_write(self, message, level):
        self.log_text = self.log_text + message

    #####################
    # key bindings display
    def display_bindings(self):
        pass
