#! /usr/bin/env python
'''
global_mode.py: Global input mode bindings

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from mfp.gui_main import MFPGUI
from mfp import log
from mfp.gui.collision import collision_check
from ..input_mode import InputMode
from .label_edit import LabelEditMode
from .transient import TransientMessageEditMode
from .enum_control import EnumEditMode
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

        InputMode.__init__(self, "Global input bindings")

        # global keybindings
        self.bind("!", self.transient_msg, "Send message to selection")
        self.bind("~", self.toggle_console, "Show/hide log and console")
        self.bind("`", self.toggle_tree, "Show/hide left side info")

        self.bind("PGUP", self.window.layer_select_up, "Select higher layer")
        self.bind("PGDN", self.window.layer_select_down, "Select lower layer")
        self.bind("C-PGUP", self.window.patch_select_prev, "Select higher patch")
        self.bind("C-PGDN", self.window.patch_select_next, "Select lower patch")

        self.bind("C-i", self.inspect, "Open state inspector")
        self.bind('C-f', self.window.patch_new, "Create a new patch")
        self.bind('C-o', self.open_file, "Load file into new patch")
        self.bind('C-s', self.save_file, "Save patch to file")
        self.bind('C-p', self.save_as_lv2, "Save patch as LV2 plugin")
        self.bind('C-w', self.patch_close, "Close current patch")
        self.bind('C-q', self.quit, "Quit")

        self.bind('C-A-.', self.toggle_pause, "Pause/unpause execution")

        self.bind("M1DOWN", lambda: self.selbox_start(None), "Start selection box")
        self.bind("M1-MOTION", lambda: self.selbox_motion(True), "Drag selection box")
        self.bind("M1UP", self.selbox_end, "End selection box")

        self.bind("S-M1DOWN", lambda: self.selbox_start(True), "Start add-to-selection box")
        self.bind("S-M1-MOTION", lambda: self.selbox_motion(True), "Drag add-to-selection box")
        self.bind("S-M1UP", self.selbox_end, "End selection box")

        self.bind("C-M1DOWN", lambda: self.selbox_start(False),
                  "Start toggle-selection box")
        self.bind("C-M1-MOTION", lambda: self.selbox_motion(False),
                  "Drag toggle-selection box")
        self.bind("C-M1UP", self.selbox_end, "End toggle-selection box")

        self.bind("S-C-M1DOWN", self.drag_start, "Begin dragging viewport")
        self.bind("S-C-M1-MOTION", self.drag_motion, "Drag viewport")
        self.bind("S-C-M1UP", self.drag_end, "End drag viewport")

        self.bind('+', lambda: self.window.relative_zoom(1.25), "Zoom view in")
        self.bind('=', lambda: self.window.relative_zoom(1.25), "Zoom view in")
        self.bind('-', lambda: self.window.relative_zoom(0.8), "Zoom view out")
        self.bind('SCROLLUP', lambda: self.scroll_zoom(1.06), "Zoom view in")
        self.bind('SCROLLDOWN', lambda: self.scroll_zoom(0.95), "Zoom view out")
        self.bind('SCROLLSMOOTHUP', lambda: self.scroll_zoom(1.015), "Zoom view in")
        self.bind('SCROLLSMOOTHDOWN', lambda: self.scroll_zoom(0.985), "Zoom view out")
        self.bind('C-0', self.window.reset_zoom, "Reset view position and zoom")
        self.bind("HOVER", lambda: self.hover(False))
        self.bind("S-HOVER", lambda: self.hover(True))

        self.bind('C-.', self.force_reset, "Reset all modifier keys and input modes")
        self.bind('S-C-.', self.force_reset, "Reset all modifier keys and input modes")
        self.bind('M1-C-.', self.force_reset, "Reset all modifier keys and input modes")

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

    async def toggle_tree(self):
        await self.window.signal_emit("toggle-info-panel")
        return False

    async def force_reset(self):
        await self.window.unselect_all()

        while self.manager.minor_modes:
            self.manager.disable_minor_mode(self.manager.minor_modes[0])

        self.manager.keyseq.mouse_buttons = set()
        self.manager.keyseq.mod_keys = set()

    async def transient_msg(self):
        from ..message_element import TransientMessageElement
        if self.window.selected:
            return await self.window.add_element(TransientMessageElement.build)
        return False

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

    async def save_file(self):
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
        await self.window.get_prompted_input("File name to save: ", cb, default_filename)

    async def save_as_lv2(self):
        patch = self.window.selected_patch
        default_plugname = 'mfp_' + patch.obj_name

        async def cb(plugname):
            if plugname:
                await MFPGUI().mfp.save_lv2(patch.obj_name, plugname)
        await self.window.get_prompted_input("Plugin name to save: ", cb, default_plugname)

    async def open_file(self):
        async def cb(fname):
            await MFPGUI().mfp.open_file(fname)
        await self.window.get_prompted_input("File name to load: ", cb)

    def drag_start(self):
        self.drag_started = True
        px = self.manager.pointer_ev_x
        py = self.manager.pointer_ev_y

        self.drag_last_x = px
        self.drag_last_y = py
        return True

    def drag_motion(self):
        if self.drag_started is False:
            return False

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
        return True

    async def selbox_start(self, select_mode):
        px = self.manager.pointer_x
        py = self.manager.pointer_y
        enclosed = []
        selection_corners = [(px, py), (px+1, py), (px+1, py+1), (px, py+1)]

        if self.window.selected_window != "canvas":
            return

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
        dx = px - self.drag_last_x
        dy = py - self.drag_last_y
        self.drag_last_x = px
        self.drag_last_y = py

        if self.selection_drag_started:
            for obj in self.window.selected:
                if obj.editable and obj.display_type != 'connection':
                    await obj.drag(dx, dy)
            return True

        enclosed = self.window.show_selection_box(
            self.drag_start_x, self.drag_start_y,
            self.drag_last_x, self.drag_last_y
        )

        for obj in enclosed:
            if select_mode:
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

    async def selbox_end(self):
        if self.selection_drag_started:
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
            await self.window.get_prompted_input("Patch has unsaved changes. Close anyway? [yN]",
                                           close_confirm, '')
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
            await self.window.get_prompted_input(
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
