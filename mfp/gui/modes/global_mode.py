#! /usr/bin/env python
'''
global_mode.py: Global input mode bindings

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import inspect
from mfp.gui_main import MFPGUI, backend_name
from mfp import log
from ..input_mode import InputMode
from .label_edit import LabelEditMode
from .transient import TransientMessageEditMode
from .enum_control import EnumEditMode
from .tile_manager import TileManagerMode
from ..input_manager import InputManager


class GlobalMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window

        self.allow_selection_drag = True
        self.selection_drag_started = False
        self.drag_started = False
        self.selbox_started = False
        self.selbox_changed = []
        self.drag_start_x = None
        self.drag_start_y = None
        self.drag_last_x = None
        self.drag_last_y = None
        self.drag_target = None

        self.snoop_conn = None
        self.snoop_source = None

        self.search_interactive_matches = []
        self.search_interactive_position = 0

        self.tile_manager_mode = None

        InputMode.__init__(self, "Global input bindings", "Global")

    @classmethod
    def init_bindings(cls):
        # Always in node context menu
        cls.bind(
            "send-message", cls.transient_msg, helptext="Send message to selection",
            keysym="!",
            menupath="Context > Send message"
        )
        cls.bind(
            "clear-counters", cls.clear_counters, helptext="Clear error counters",
            keysym="C-k",
            menupath="Context > Clear counters"
        )
        cls.bind(
            "open-help", cls.open_help, helptext="Clear error counters",
            keysym="F1",
            menupath="Context > ||Help"
        )
        # global keybindings
        cls.bind(
            "search-interactive", cls.search_interactive,
            helptext="Find elements matching search string",
            keysym="/",
        )
        cls.bind(
            "search-interactive-select-next", cls.search_interactive_next,
            helptext="Select next element matching search string",
            keysym="S-RET",
        )
        cls.bind(
            "search-interactive-select-prev", cls.search_interactive_prev,
            helptext="Select previous element matching search string",
            keysym="?",
        )
        cls.bind(
            "search-interactive-select-all", cls.search_interactive_all,
            helptext="Select all elements matching search string",
            keysym="A-RET"
        )
        cls.bind(
            "toggle-console", cls.toggle_console, helptext="Show/hide log and console",
            keysym="~",
            menupath="Window > |||[x]Log/Python console"
        )
        cls.bind(
            "toggle-info", cls.toggle_info, helptext="Show/hide info panel",
            keysym="`",
            menupath="Window > |||[x]Info panel"
        )
        cls.bind(
            "toggle-inspector", cls.inspect, helptext="Open state inspector",
            keysym="C-i",
            menupath="Window > |||UI debugger"
        )
        cls.bind(
            "layer-select-up", lambda mode: mode.window.layer_select_up(), helptext="Select higher layer",
            keysym="PGUP",
            menupath="Layer > Select up"
        )
        cls.bind(
            "layer-select-down", lambda mode: mode.window.layer_select_down(), helptext="Select lower layer",
            keysym="PGDN",
            menupath="Layer > Select down"
        )
        cls.bind(
            "patch-select-prev", lambda mode: mode.window.patch_select_prev(), helptext="Select higher patch",
            keysym="C-PGUP",
        )
        cls.bind(
            "patch-select-next", lambda mode: mode.window.patch_select_next(), helptext="Select lower patch",
            keysym="C-PGDN"
        )
        cls.bind(
            "new-patch", lambda mode: mode.window.patch_new(), helptext="Create a new patch",
            keysym="C-f",
            menupath="File > New"
        )
        cls.bind(
            "open-patch", cls.open_file, helptext="Load file into new patch",
            keysym="C-o",
            menupath="File > Open..."
        )
        cls.bind(
            "save-patch", cls.save_file, helptext="Save patch to file",
            keysym="C-s",
            menupath="File > |Save..."
        )
        cls.bind(
            "save-lv2", cls.save_as_lv2, helptext="Save patch as LV2 plugin",
            keysym="C-p",
            menupath="File > |Save as LV2..."
        )
        cls.bind(
            "cmd-entry", cls.cmdline, helptext="Enter a command",
            keysym=":", menupath="File > ||Command line"
        )
        cls.bind(
            "toggle-pause", cls.toggle_pause, helptext="Pause/unpause execution",
            keysym="C-A-.", menupath="File > ||[]Pause/unpause execution"
        )
        cls.bind(
            "reset-input", cls.force_reset, helptext="Reset all modifier keys and input modes",
            keysym="C-.", menupath="File > ||Reset input modes"
        )
        cls.bind(
            "close-patch", cls.patch_close, helptext="Close current patch",
            keysym="C-w",
            menupath="File > |||Close"
        )
        cls.bind(
            "q", cls.quit, helptext="Quit", keysym="C-q", menupath="File > |||Quit"
        )
        cls.bind(
            "zoom-in", lambda mode: mode.window.relative_zoom(1.25), helptext="Zoom view in",
            keysym="+", menupath="Window > Zoom in"
        )
        cls.bind(
            "zoom-in-alt", lambda mode: mode.window.relative_zoom(1.25), helptext="Zoom view in",
            keysym="="
        )
        cls.bind(
            "zoom-out", lambda mode: mode.window.relative_zoom(0.8), helptext="Zoom view out",
            keysym="-", menupath="Window > Zoom out"
        )
        cls.bind(
            "zoom-reset", cls.reset_zoom, helptext="Reset view position and zoom",
            keysym="C-0", menupath="Window > Reset zoom + position"
        )
        cls.bind(
            "selbox-start", lambda mode: mode.selbox_start(None), helptext="Start selection box",
            keysym="M1DOWN"
        )
        cls.bind(
            "selbox-start-M3", lambda mode: mode.selbox_start(None), helptext="Context menu",
            keysym="M3DOWN"
        )
        cls.bind(
            "selbox-motion", lambda mode: mode.selbox_motion(True), helptext="Drag selection box",
            keysym="M1-MOTION"
        )
        cls.bind(
            "selbox-alt-insert", lambda mode: mode.selbox_end("insert"),
            helptext="Insert selection into connection",
            keysym="A-M1UP"
        )
        cls.bind(
            "selbox-end", cls.selbox_end, helptext="End selection box",
            keysym="M1UP"
        )
        cls.bind(
            "selbox-add-start", lambda mode: mode.selbox_start(True),
            helptext="Start add-to-selection box",
            keysym="S-M1DOWN"
        )
        cls.bind(
            "selbox-alt-start", lambda mode: mode.selbox_start("insert"), helptext="Start auto-connect",
            keysym="A-M1DOWN"
        )
        cls.bind(
            "selbox-add-motion", lambda mode: mode.selbox_motion(True), helptext="Drag add-to-selection box",
            keysym="S-M1-MOTION"
        )
        cls.bind(
            "selbox-alt-motion", lambda mode: mode.selbox_motion("insert"), helptext="Drag auto-connect node",
            keysym="A-M1-MOTION"
        )
        cls.bind(
            "selbox-toggle-start", lambda mode: mode.selbox_start(False),
            helptext="Start toggle-selection box",
            keysym="C-M1DOWN",
        )
        cls.bind(
            "selbox-toggle-drag", lambda mode: mode.selbox_motion(False),
            helptext="Drag toggle-selection box",
            keysym="C-M1-MOTION",
        )
        cls.bind(
            "selbox-toggle-end", cls.selbox_end, helptext="End toggle-selection box",
            keysym="C-M1UP",
        )
        cls.bind(
            "viewport-drag-start", cls.drag_start, helptext="Begin dragging viewport",
            keysym="S-C-M1DOWN"
        )
        cls.bind(
            "viewport-drag-motion", cls.drag_motion, helptext="Drag viewport",
            keysym="S-C-M1-MOTION"
        )
        cls.bind(
            "viewport-drag-end", cls.drag_end, helptext="End drag viewport",
            keysym="S-C-M1UP"
        )
        cls.bind(
            "zoom-in-scroll", lambda mode: mode.scroll_zoom(1.06), helptext="Zoom view in",
            keysym="SCROLLUP"
        )
        cls.bind(
            "zoom-out-scroll", lambda mode: mode.scroll_zoom(0.95), helptext="Zoom view out",
            keysym="SCROLLDOWN"
        )
        cls.bind(
            "zoom-in-scroll-fine", lambda mode: mode.scroll_zoom(1.015), helptext="Zoom view in",
            keysym="SCROLLSMOOTHUP"
        )
        cls.bind(
            "zoom-out-scroll-fine", lambda mode: mode.scroll_zoom(0.985), helptext="Zoom view out",
            keysym="SCROLLSMOOTHDOWN"
        )
        cls.bind(
            "hover", lambda mode: mode.hover(False),
            keysym="HOVER"
        )
        cls.bind(
            "hover-alt", lambda mode: mode.hover(True),
            keysym="S-HOVER"
        )
        cls.bind(
            "reset-input", cls.force_reset, helptext="Reset all modifier keys and input modes",
            keysym="S-C-."
        )
        cls.bind(
            "reset-input", cls.force_reset, helptext="Reset all modifier keys and input modes",
            keysym="M1-C-."
        )
        cls.bind(
            "toggle-snoop",
            lambda mode: mode.toggle_snoop(),
            helptext="Toggle snooping messages on connection",
            keysym="$"
        )

        # imgui only
        if backend_name == "imgui":
            cls.bind(
                "tile-control", cls.tile_manager_prefix,
                keysym="C-a"
            )

    def tile_manager_prefix(self):
        if not self.tile_manager_mode:
            self.tile_manager_mode = TileManagerMode(self.window)
        return self.manager.enable_minor_mode(self.tile_manager_mode)

    async def cmdline(self):
        """
        look up actions by their label and execute them.
        Pass args as additional binding args (may replace
        params the action usually gets by interactive prompt)
        """
        async def cb(txt):
            if txt.startswith("eval "):
                resp = eval(txt[5:])
                log.debug(f"[eval] {txt[5:]} --> {resp}")
            else:
                cmd, *rest = txt.split(' ', 1)
                binding = InputMode._bindings_by_label.get(cmd.strip())
                if not binding:
                    return
                mode_binding = self.window.input_mgr.binding_enabled(
                    binding.mode, binding.keysym
                )
                argtpl = ()
                if rest and rest[0]:
                    argtpl = eval(f"({rest[0]},)")
                if mode_binding:
                    result = mode_binding.action(*argtpl)
                    if inspect.isawaitable(result):
                        await result

        await self.window.cmd_get_input(":", cb, '')
        return True

    async def clear_counters(self):
        if self.window.selected:
            for elt in self.window.selected:
                await MFPGUI().mfp.send_methodcall(elt.obj_id, 0, "reset_counts")

    def reset_zoom(self):
        self.window.reset_zoom()
        return True

    def scroll_zoom(self, ratio):
        if "scroll-zoom" in self.window.motion_overrides:
            return
        self.window.relative_zoom(ratio)

    def inspect(self):
        """
        show the flopsy state inspector (debugger)
        """
        from flopsy import Inspector
        if self.window.inspector is None:
            self.window.inspector = Inspector(
                title="State inspector", event_loop=MFPGUI().async_task.asyncio_loop
            )
        self.window.inspector.focus()

    async def toggle_console(self):
        await self.window.signal_emit("toggle-console")
        return False

    async def toggle_info(self):
        await self.window.signal_emit("toggle-info-panel")
        return False

    async def force_reset(self):
        await self.window.unselect_all()

        while self.manager.minor_modes:
            self.manager.disable_minor_mode(self.manager.minor_modes[0])

        self.manager.keyseq.mouse_buttons = set()
        self.manager.keyseq.mod_keys = set()

    async def transient_msg(self, message=None):
        from ..message_element import TransientMessageElement
        rv = False
        if self.window.selected:
            rv = await self.window.add_element(TransientMessageElement.build)

        # if message is not none, this binding is being invoked from
        # the cmdline
        if message is not None:
            for key in list(f"{message!r}") + ["RET"]:
                self.window.input_mgr.handle_keysym(key)
        return rv

    async def hover(self, details):
        from ..base_element import BaseElement
        for m in self.manager.minor_modes:
            if (
                m.enabled and isinstance(
                    m, (TransientMessageEditMode, LabelEditMode, EnumEditMode)
                )
            ):
                details = False

        o = self.manager.pointer_obj
        try:
            if o is not None and o.obj_state == BaseElement.OBJ_COMPLETE:
                await o.show_tip(self.manager.pointer_x, self.manager.pointer_y, details)
        except Exception:
            pass
        return False

    async def save_file(self, filename=None):
        import os.path
        patch = self.window.selected_patch
        if patch.last_filename is None:
            default_filename = patch.obj_name + '.mfp'
        else:
            default_filename = patch.last_filename

        async def cb(fname):
            if fname:
                patch.last_filename = fname
                if fname != default_filename:
                    basefile = os.path.basename(fname)
                    parts = os.path.splitext(basefile)
                    newname = parts[0]
                    patch.obj_name = newname
                    await MFPGUI().mfp.rename_obj(patch.obj_id, newname)
                    prms = patch.synced_params()
                    await MFPGUI().mfp.set_params(patch.obj_id, prms)
                    self.window.refresh(patch)
                await MFPGUI().mfp.save_file(patch.obj_name, fname)
        if filename is None:
            await self.window.cmd_get_input(
                "File name to save: ", cb, default_filename, filename="save"
            )
        else:
            await cb(filename)

    async def save_as_lv2(self, filename=None):
        patch = self.window.selected_patch
        default_plugname = 'mfp_' + patch.obj_name

        async def cb(plugname):
            if plugname:
                await MFPGUI().mfp.save_lv2(patch.obj_name, plugname)
        if filename is None:
            await self.window.cmd_get_input(
                "Plugin name to save: ", cb, default_plugname, filename="save"
            )
        else:
            await cb(filename)

    async def open_file(self, filename=None):
        async def cb(fname):
            await MFPGUI().mfp.open_file(fname)

        if filename is None:
            await self.window.cmd_get_input(
                "File name to load: ", cb, filename="open"
            )
        else:
            await cb(filename)

    def drag_start(self):
        self.drag_started = True
        px = self.manager.pointer_ev_x
        py = self.manager.pointer_ev_y

        self.drag_last_x = px
        self.drag_last_y = py
        self.window.viewport_drag_active = True
        return True

    def drag_motion(self):
        if self.drag_started is False:
            return False

        self.window.viewport_drag_active = True
        px = self.manager.pointer_ev_x
        py = self.manager.pointer_ev_y

        dx = px - self.drag_last_x
        dy = py - self.drag_last_y

        self.drag_last_x = px
        self.drag_last_y = py

        self.window.move_view(dx, dy)
        return True

    def drag_end(self):
        self.drag_started = False
        self.window.viewport_drag_active = False
        return True

    async def selbox_start(self, select_mode):
        px = self.manager.pointer_x
        py = self.manager.pointer_y

        if self.window.backend_name == "imgui":
            from imgui_bundle import imgui_node_editor as nedit
            if (
                self.window.selected_window != "canvas"
                or self.window.main_menu_open
                or self.window.context_menu_open
                or nedit.get_hovered_pin().id()
            ):
                return False
            self.window.imgui_tile_selected = True

        if select_mode is None:
            if self.manager.pointer_obj is not None:
                if self.manager.pointer_obj not in self.window.selected:
                    await self.window.unselect_all()
                    await self.window.select(self.manager.pointer_obj)
                    raise InputManager.InputNeedsRequeue()
                if self.allow_selection_drag:
                    self.selection_drag_started = True
                    for obj in self.window.selected:
                        if obj.editable and obj.display_type != 'connection':
                            obj.drag_start()
            else:
                await self.window.unselect_all()
                self.selbox_started = True
        elif select_mode is True:
            if (self.manager.pointer_obj and self.manager.pointer_obj not in self.window.selected):
                await self.window.select(self.manager.pointer_obj)
            self.selbox_started = True
        elif select_mode == "insert":
            if self.allow_selection_drag:
                self.selection_drag_started = True
                for obj in self.window.selected:
                    if obj.editable and obj.display_type != 'connection':
                        obj.drag_start()
        else:
            if self.manager.pointer_obj in self.window.selected:
                await self.window.unselect(self.manager.pointer_obj)
            self.selbox_started = True

        px = self.manager.pointer_x
        py = self.manager.pointer_y

        self.drag_start_x = px
        self.drag_start_y = py
        self.drag_last_x = px
        self.drag_last_y = py
        return True

    async def selbox_motion(self, select_mode):
        if not (self.selbox_started or self.selection_drag_started):
            return False

        px = self.manager.pointer_x
        py = self.manager.pointer_y
        dx = px - self.drag_start_x
        dy = py - self.drag_start_y

        self.drag_last_x = px
        self.drag_last_y = py

        if self.selection_drag_started:
            if (
                select_mode == "insert"
                and len(self.window.selected) == 1
            ):
                sel = self.window.selected[0]
                src_obj = src_port = dest_obj = dest_port = None
                src_conn = dest_conn = None
                for c in sel.connections_in:
                    if c.port_2 == 0:
                        if src_obj is None:
                            src_obj = c.obj_1
                            src_port = c.port_1
                            src_conn = c
                        elif src_obj != c.obj_1:
                            src_obj = False
                    else:
                        src_obj = False
                for c in sel.connections_out:
                    if c.port_1 == 0:
                        if dest_obj is None:
                            dest_obj = c.obj_2
                            dest_port = c.port_2
                            dest_conn = c
                        elif dest_obj != c.obj_2:
                            dest_obj = False
                    else:
                        dest_obj = False
                if src_obj and dest_obj:
                    sel.connections_in = []
                    sel.connections_out = []
                    await dest_conn.delete()
                    await src_conn.delete()
                    await self._connect(src_obj, src_port, dest_obj, dest_port)

            for obj in self.window.selected:
                if obj.editable and obj.display_type != 'connection':
                    await obj.move(
                        obj.drag_start_x + dx,
                        obj.drag_start_y + dy
                    )
            return True

        enclosed = self.window.show_selection_box(
            self.drag_start_x, self.drag_start_y,
            self.drag_last_x, self.drag_last_y
        )

        for obj in enclosed:
            if select_mode is True:
                if obj not in self.window.selected:
                    if obj not in self.selbox_changed:
                        self.selbox_changed.append(obj)
                    await self.window.select(obj)
            else:
                if obj not in self.selbox_changed:
                    self.selbox_changed.append(obj)
                    if obj in self.window.selected:
                        await self.window.unselect(obj)
                    else:
                        await self.window.select(obj)
        new_changed = []
        for obj in self.selbox_changed:
            if obj not in enclosed:
                if obj in self.window.selected:
                    await self.window.unselect(obj)
                else:
                    await self.window.select(obj)
            else:
                new_changed.append(obj)
        self.selbox_changed = new_changed

        return True

    async def _connect(self, src_obj, src_port, dest_obj, dest_port):
        from ..connection_element import ConnectionElement
        connection = ConnectionElement.build(
            self.window,
            src_obj, src_port,
            dest_obj, dest_port
        )
        self.window.register(connection)
        src_obj.connections_out.append(connection)
        dest_obj.connections_in.append(connection)

        await MFPGUI().mfp.connect(
            src_obj.obj_id, src_port, dest_obj.obj_id, dest_port
        )

    async def selbox_end(self, select_mode=None):
        from ..connection_element import ConnectionElement
        if self.selection_drag_started:
            if (
                select_mode == "insert"
                and len(self.window.selected) == 1
                and self.window.selected[0].num_outlets > 0
                and self.window.selected[0].editable
                and not isinstance(self.window.selected[0], ConnectionElement)
            ):
                selected = self.window.selected[0]
                overlapped = self.window.find_contained(
                    selected.position_x, selected.position_y,
                    selected.position_x + selected.width,
                    selected.position_y + selected.height
                )
                overlapped_connections = [
                    o for o in overlapped
                    if (
                        isinstance(o, ConnectionElement)
                        and o.obj_state == ConnectionElement.OBJ_COMPLETE
                        and o not in selected.connections_in
                        and o not in selected.connections_out
                    )
                ]
                if len(overlapped_connections) == 1:
                    conn = overlapped_connections[0]
                    source_obj = conn.obj_1
                    source_port = conn.port_1
                    dest_obj = conn.obj_2
                    dest_port = conn.port_2
                    await conn.delete()
                    await self._connect(source_obj, source_port, selected, 0)
                    await self._connect(selected, 0, dest_obj, dest_port)

            for obj in self.window.selected:
                if obj.editable and obj.display_type != 'connection':
                    await obj.drag_end()
                obj.send_params()

        self.selbox_started = False
        self.selection_drag_started = False
        self.selbox_changed = []
        self.window.hide_selection_box()
        return True

    async def patch_close(self):
        async def close_confirm(answer):
            if answer is not None:
                aa = answer.strip().lower()
                if aa in ['y', 'yes']:
                    await self.window.patch_close()

        p = self.window.selected_patch
        if await MFPGUI().mfp.has_unsaved_changes(p.obj_id):
            await self.window.cmd_get_input(
                "Patch has unsaved changes. Close anyway? [yN]",
                close_confirm, ''
            )
        else:
            await self.window.patch_close()

    async def quit(self):
        def quit_confirm(answer):
            if answer is not None:
                aa = answer.strip().lower()
                if aa in ['y', 'yes']:
                    MFPGUI().async_task(self.window.quit())

        allpatches = await MFPGUI().mfp.open_patches()
        clean = True
        for p in allpatches:
            if await MFPGUI().mfp.has_unsaved_changes(p):
                clean = False
        if not clean:
            await self.window.cmd_get_input(
                "There are patches with unsaved changes. Quit anyway? [yN]",
                quit_confirm,
                ''
            )
        else:
            await self.window.quit()

    async def toggle_pause(self):
        try:
            paused = await MFPGUI().mfp.toggle_pause()
            if paused:
                log.warning("Execution of all patches paused")
            else:
                log.warning("Execution of all patches resumed")
        except Exception as e:
            print("Caught exception", e)

    async def toggle_snoop(self):
        from mfp.gui.connection_element import ConnectionElement

        if not self.snoop_conn:
            if self.window.selected:
                cc = [c for c in self.window.selected if isinstance(c, ConnectionElement)]
                if len(cc) == 1:
                    self.snoop_conn = cc[0]
                    self.snoop_conn.snoop = True
                    self.snoop_source = self.snoop_conn.obj_1
                    self.snoop_source.send_params()
                    self.window.hud_write(f"Snooping on connection {self.snoop_conn}")
        else:
            self.snoop_conn.snoop = False
            self.snoop_source.send_params()
            self.snoop_conn = None
            self.snoop_source = None
            self.window.hud_write("Snooping disabled")

    async def search_interactive(self):
        async def search_changed(newval, incremental=True):
            matches = []
            for element in self.window.objects:
                if not newval:
                    element.highlight_text = None
                    continue
                if (
                    newval in (element.obj_type or '')
                    or newval in (element.obj_name or '')
                    or newval in (element.obj_args or '')
                ):
                    matches.append(element)
                    element.highlight_text = newval
                else:
                    element.highlight_text = None

            if incremental:
                if matches != self.search_interactive_matches:
                    self.search_interactive_position = 0
                    self.search_interactive_matches = matches
            else:
                if len(self.search_interactive_matches):
                    await self.window.select(
                        self.search_interactive_matches[
                            min(self.search_interactive_position, len(self.search_interactive_matches))
                        ]
                    )

        await self.window.cmd_get_input(
            "/", search_changed, '', incremental=True, space=False
        )

    async def search_interactive_next(self, forward=True):
        if not self.search_interactive_matches:
            return
        offset = 1
        if not forward:
            offset = -1
        self.search_interactive_position = (
            (self.search_interactive_position + offset) % len(self.search_interactive_matches)
        )
        await self.window.unselect_all()
        await self.window.select(
            self.search_interactive_matches[self.search_interactive_position]
        )

    async def search_interactive_prev(self):
        self.search_interactive_next(forward=False)

    async def search_interactive_all(self):
        for e in self.search_interactive_matches:
            await self.window.select(e)

    async def open_help(self):
        if len(self.window.selected) == 1:
            help_patch = await self.window.selected[0].get_help_patch()
            log.debug(f"Opening help patch {help_patch}")
            await MFPGUI().mfp.open_file(help_patch)
