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
from mfp.gui.connection_element import ConnectionElement
from mfp.gui.modes.patch_edit import PatchEditMode
from ..app_window import AppWindow, AppWindowImpl
from .inputs import imgui_process_inputs, imgui_key_map
from .sdl2_renderer import ImguiSDL2Renderer as ImguiRenderer
from ..event import EnterEvent, LeaveEvent
from . import info_panel, menu_bar

MAX_RENDER_US = 200000


class ImguiAppWindowImpl(AppWindow, AppWindowImpl):
    backend_name = "imgui"
    motion_overrides = ["drag", "scroll-zoom", "canvas_pos"]

    INIT_WIDTH = 900
    INIT_HEIGHT = 700

    INIT_INFO_PANEL_WIDTH = 300
    INIT_CONSOLE_PANEL_HEIGHT = 150
    MENU_HEIGHT = 21

    def __init__(self, *args, **kwargs):
        self.imgui_impl = None
        self.imgui_renderer = None
        self.imgui_repeating_keys = {}
        self.imgui_needs_reselect = []

        self.info_panel_id = None
        self.info_panel_visible = True
        self.info_panel_width = self.INIT_INFO_PANEL_WIDTH

        self.console_panel_id = None
        self.console_panel_visible = True
        self.console_panel_height = self.INIT_CONSOLE_PANEL_HEIGHT

        self.canvas_panel_id = None
        self.canvas_panel_width = self.INIT_WIDTH - self.INIT_INFO_PANEL_WIDTH
        self.canvas_panel_height = self.INIT_HEIGHT - self.INIT_CONSOLE_PANEL_HEIGHT

        self.frame_count = 0
        self.frame_timestamps = []
        self.viewport_box_nodes = None

        self.selected_window = "canvas"
        self.inspector = None
        self.log_text = ""

        super().__init__(*args, **kwargs)

        self.signal_listen("motion-event", self.handle_motion)

    async def handle_motion(self, target, signal, event, *rest):
        """
        Listener to set the currently-active panel based on pointer position
        """
        prev_pointer_obj = event.target
        new_pointer_obj = prev_pointer_obj
        if self.console_panel_visible:
            if event.y >= self.window_height - self.console_panel_height:
                if prev_pointer_obj != self.console_manager:
                    new_pointer_obj = self.console_manager
                    self.selected_window = "console"
        if not new_pointer_obj and self.info_panel_visible:
            if event.x < self.canvas_panel_width:
                new_pointer_obj = self
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
            # idle while there are no input events
            loop_start_time = datetime.now()
            while True:
                keep_going, events_processed = await self.imgui_impl.process_events()
                if events_processed or not keep_going:
                    break
                if datetime.now() > loop_start_time + timedelta(microseconds=MAX_RENDER_US):
                    break
                if Store.last_activity_time() > loop_start_time:
                    break
                await asyncio.sleep(.01)

            self.imgui_renderer.process_inputs()

            if not keep_going:
                continue

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
        self.close_in_progress = True

    #####################
    # renderer
    def render(self):
        from mfp.gui.modes.global_mode import GlobalMode
        from mfp.gui.modes.console_mode import ConsoleMode
        keep_going = True
        menu_height = self.MENU_HEIGHT

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

            _, menu_height = imgui.get_cursor_pos()

        # menu bar
        ########################################

        canvas_origin = (1, menu_height + 1)

        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0, 0))

        ########################################
        # full-screen window containing the dockspace
        imgui.set_next_window_size((self.window_width, self.window_height - 2*menu_height))
        imgui.set_next_window_pos((0, menu_height))

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
        self.canvas_panel_width = canvas_size[0]
        self.canvas_panel_height = canvas_size[1]

        imgui.begin(
            "canvas",
            flags=(
                imgui.WindowFlags_.no_collapse
                | imgui.WindowFlags_.no_move
                | imgui.WindowFlags_.no_title_bar
            ),
        )
        cursor_x, cursor_y = imgui.get_cursor_pos()
        if imgui.is_window_hovered(imgui.FocusedFlags_.child_windows):
            self.selected_window = "canvas"
            if not isinstance(self.input_mgr.global_mode, GlobalMode):
                self.input_mgr.global_mode = GlobalMode(self)
                self.input_mgr.major_mode.enable()

        nedit.push_style_color(
            nedit.StyleColor.bg,
            self.get_color('canvas-color').to_rgbaf()
        )
        nedit.push_style_color(
            nedit.StyleColor.node_border,
            self.get_color('stroke-color').to_rgbaf()
        )
        nedit.push_style_color(
            nedit.StyleColor.sel_node_border, (0, 0, 0, 0)
        )
        nedit.push_style_color(
            nedit.StyleColor.sel_link_border, (0, 0, 0, 0)
        )
        nedit.push_style_color(
            nedit.StyleColor.hov_node_border,
            self.get_color('stroke-color:hover').to_rgbaf()
        )
        nedit.push_style_color(
            nedit.StyleColor.hov_link_border,
            self.get_color('stroke-color:hover').to_rgbaf()
        )

        nedit.begin("canvas_editor", (0.0, 0.0))

        conf = nedit.get_config()

        # disable NodeEditor dragging of nodes when not in edit mode
        if isinstance(self.input_mgr.major_mode, PatchEditMode):
            conf.drag_button_index = 0
        else:
            conf.drag_button_index = 3

        # reselect nodes if needed
        if self.imgui_needs_reselect:
            nedit.clear_selection()
            for obj in self.imgui_needs_reselect:
                nedit.select_node(obj.node_id, True)
            self.imgui_needs_reselect = []

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
        # viewport management
        # this is janky. We create an invisible upper-left and lower-right
        # node that we will use wth zoom_to_selection()

        # create nodes if needed
        if self.viewport_box_nodes is None:
            min_node_id = nedit.NodeId.create()
            max_node_id = nedit.NodeId.create()
            self.viewport_box_nodes = (min_node_id, max_node_id)

        current_zoom = 1.0 / nedit.get_current_zoom()
        viewport_x, viewport_y = nedit.screen_to_canvas(canvas_origin)

        need_navigate = False
        need_zoom = False

        if current_zoom != self.zoom:
            if self.viewport_zoom_set:
                need_navigate = True
                need_zoom = True
            else:
                self.zoom = current_zoom

        self.viewport_zoom_set = False

        if self.view_x != viewport_x or self.view_y != viewport_y:
            if self.viewport_pos_set:
                need_navigate = True
            else:
                self.view_x = viewport_x
                self.view_y = viewport_y

        self.viewport_pos_set = False

        if need_navigate:
            window_size = (self.canvas_panel_width, self.canvas_panel_height)
            # navigate_to_selection expands the selection box by 10%
            EXP = 1.10
            dw = 0.5 * (1.0 - 1.0/EXP) * window_size[0]
            dh = 0.5 * (1.0 - 1.0/EXP) * window_size[1]
            upper_left = (
                self.view_x + dw,
                self.view_y + dh
            )
            canvas_dimensions = (
                (1.0 / self.zoom) * window_size[0],
                (1.0 / self.zoom) * window_size[1]
            )
            lower_right = (
                self.view_x + canvas_dimensions[0] - 2*dw,
                self.view_y + canvas_dimensions[1] - 2*dh
            )
            nedit.push_style_var(nedit.StyleVar.node_rounding, 0)
            nedit.push_style_var(nedit.StyleVar.node_padding, (0, 0, 0, 0))
            nedit.push_style_var(nedit.StyleVar.node_border_width, 0)

            nedit.set_node_position( self.viewport_box_nodes[0], upper_left)
            nedit.begin_node(self.viewport_box_nodes[0])
            nedit.end_node()

            nedit.set_node_position(
                self.viewport_box_nodes[1], lower_right
            )
            nedit.begin_node(self.viewport_box_nodes[1])
            nedit.end_node()
            nedit.pop_style_var(3)

            # save the current selection, then clear it
            selection = [
                obj for obj in self.objects if obj.selected
            ]
            for obj in selection:
                nedit.deselect_node(obj.node_id)

            # select the upper-left and lower-right nodes
            for obj_id in self.viewport_box_nodes:
                nedit.select_node(obj_id, True)

            # navigate to them
            nedit.navigate_to_selection(need_zoom, 0)
            self.imgui_needs_reselect = selection

        #############################
        # creation of links (by click-drag)
        if nedit.begin_create():
            start_pin = nedit.PinId.create()
            end_pin = nedit.PinId.create()
            if nedit.query_new_link(start_pin, end_pin):
                if start_pin and end_pin and nedit.accept_new_item():
                    start_obj, start_port_id = all_pins.get(start_pin.id(), (None, None))
                    end_obj, end_port_id = all_pins.get(end_pin.id(), (None, None))
                    MFPGUI().async_task(
                        self.render_make_connection(start_obj, start_port_id[1], end_obj, end_port_id[1])
                    )
            nedit.end_create()

        nedit.end()  # node_editor
        nedit.pop_style_color(5)

        imgui.end()

        # canvas window
        ########################################

        ########################################
        # right-side info display
        if self.info_panel_visible:
            panel_height = self.window_height - menu_height
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
            if imgui.is_window_hovered(imgui.FocusedFlags_.child_windows):
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
            if imgui.is_window_hovered(imgui.FocusedFlags_.child_windows):
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
                        (self.window_width, self.console_panel_height - menu_height),
                        imgui.InputTextFlags_.read_only
                    )
                    imgui.end_tab_item()
                if imgui.begin_tab_item("Console")[0]:
                    self.console_manager.render(self.window_width, self.console_panel_height - menu_height)
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
        imgui.pop_style_var()  # spacing

        imgui.pop_style_color() # text selected bg

        # full-screen window
        ########################################

        ########################################
        # status line at bottom
        imgui.set_next_window_size((self.window_width, menu_height))
        imgui.set_next_window_pos((0, self.window_height - menu_height))
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
            imgui.same_line()
            imgui.text(f"Zoom: {(1.0/nedit.get_current_zoom()):0.2f}")

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

    def move_view(self, dx, dy):
        self.view_x -= dx
        self.view_y -= dy
        self.viewport_pos_set = True
        return True

    def rezoom(self, **kwargs):
        if 'previous' in kwargs:
            prev_zoom = kwargs['previous']
            curr_zoom = self.zoom

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
