"""
clutter/app_window.py - Clutter backend for main app window

wrapper object delegates backend-specific methods here
"""

import pkgutil
import sys

from mfp import log
from mfp.gui.app_window import AppWindow, AppWindowImpl
from mfp.gui.collision import collision_check
from mfp.gui.colordb import ColorDB
from mfp.gui.text_widget import TextWidget
from mfp.gui.tile_manager import Tile
from mfp.gui_main import MFPGUI

from ..connection_element import ConnectionElement
from ..base_element import BaseElement
from ..patch_display import PatchDisplay

from .event import repeat_event
from .tree_display import TreeDisplay


class ClutterAppWindowImpl (AppWindow, AppWindowImpl):
    backend_name = "clutter"
    motion_overrides = []

    def render(self):
        # clutter backend does not need a render call
        pass

    def initialize(self):
        """
        Set up the Clutter window.
        """

        import gi
        gi.require_version('Gtk', '3.0')
        gi.require_version('GtkClutter', '1.0')
        gi.require_version('Clutter', '1.0')

        try:
            from gi.repository import GtkClutter

            # explicit init seems to avoid strange thread sync/blocking issues
            GtkClutter.init([])

        except Exception as e:
            log.error("Fatal error during GUI startup")
            log.debug_traceback(e)
            return

        try:
            self._init_window()

        except Exception as e:
            log.error("Caught GUI exception:", e)
            log.debug_traceback(e)
            sys.stdout.flush()

    def ready(self):
        if self.window and self.window.get_realized():
            return True
        else:
            return False

    @property
    def view_x(self):
        return self.selected_patch.display_info.view_x

    @property
    def view_y(self):
        return self.selected_patch.display_info.view_y

    @property
    def zoom(self):
        return self.selected_patch.display_info.view_zoom

    def _init_window(self):
        from gi.repository import Clutter, Gtk, GtkClutter
        # load Glade ui
        self.builder = Gtk.Builder()
        self.builder.add_from_string(pkgutil.get_data("mfp.gui", "mfp.glade").decode())

        ############################
        # backend-specific state

        self.autoplace_marker = None
        self.autoplace_layer = None

        # The HUD is the text overlay at the bottom/top of the window that
        # fades after a short display
        self.hud_history = []
        self.hud_mode_text = None
        self.hud_banner_text = None
        self.hud_banner_anim = None
        self.previous_console_position = 0
        self.next_tree_position = 1

        ############################

        ############################
        # build widgets

        # install Clutter stage in Gtk window
        self.window = self.builder.get_object("main_window")
        box = self.builder.get_object("stage_box")

        self.content_console_pane = self.builder.get_object("content_console_pane")
        self.tree_canvas_pane = self.builder.get_object("tree_canvas_pane")

        self.embed = GtkClutter.Embed.new()
        box.pack_start(self.embed, True, True, 0)
        self.embed.set_sensitive(True)
        self.stage = self.embed.get_stage()

        # FIXME compatibility with BaseElements for LabelEditMode
        self.container = self.stage

        # significant widgets we will be dealing with later
        self.bottom_notebook = self.builder.get_object("bottom_notebook")
        self.console_view = self.builder.get_object("console_text")
        self.log_view = self.builder.get_object("log_text")

        # objects for stage -- self.group gets moved/scaled to adjust
        # the view, so anything not in it will be static on the stage
        self.group = Clutter.Group()

        self.stage.add_actor(self.group)
        self.object_view = self._init_object_view()
        self.layer_view = self._init_layer_view()

        self._init_input()

        # configure Clutter stage
        self.stage.set_color(self.color_bg)
        self.stage.set_property('user-resizable', True)

        self.selection_box = None
        self.selection_box_layer = None

        # set app icon
        icon_theme = Gtk.IconTheme.get_default()
        icon_name = "mfp"
        icon_path = sys.exec_prefix + '/share/mfp/icons/'
        icon_theme.add_resource_path(icon_path)
        icon_theme.append_search_path(icon_path)
        sizes = [16, 24, 32, 48, 64, 96]
        pixbufs = [
            icon_theme.load_icon(icon_name, s, 0)
            for s in sizes
        ]
        self.window.set_icon_list(pixbufs)

        self.signal_listen("toggle-console", self._toggle_console)
        self.signal_listen("toggle-info-panel", self._toggle_info_panel)

        # show top-level window
        self.window.show_all()

        self.async_cb_events = set()

    def _init_object_view(self):
        obj_cols, selected_callback = self.init_object_view()
        object_view = TreeDisplay(self.builder.get_object("object_tree"), True, *obj_cols)
        object_view.select_cb = selected_callback
        object_view.unselect_cb = lambda obj: MFPGUI().async_task(self.unselect(obj))

        async def on_create(window, signal, element):
            if isinstance(element, PatchDisplay):
                return

            if hasattr(element, 'container') and isinstance(element.container, BaseElement):
                object_view.insert(element, (element.scope, element.container))
            elif hasattr(element, 'scope') and element.scope:
                object_view.insert(element, (element.scope, element.layer.patch))
            else:
                object_view.insert(
                    element,
                    (element.layer.scope, element.layer.patch),
                )

        def on_rename(window, signal, obj, parent):
            object_view.update(obj, parent)

        self.signal_listen("created", on_create)
        self.signal_listen("rename", on_rename)

        return object_view

    def _init_layer_view(self):
        layer_cols, selected_callback = self.init_layer_view()
        layer_view = TreeDisplay(self.builder.get_object("layer_tree"), False, *layer_cols)
        layer_view.select_cb = selected_callback
        layer_view.unselect_cb = None

        return layer_view

    def add_patch(self, patch_display, **kwargs):
        patch_display.display_info = Tile(
            title=patch_display.obj_name,
            origin_x=0,
            origin_y=0,
            width=0,
            height=0,
            view_x=0,
            view_y=0,
            view_zoom=1.0,
            page_id=0,
            tile_id=0,
            neighbors={}
        )
        super().add_patch(patch_display)

        self.layer_view.insert(patch_display, None)
        for s in patch_display.scopes:
            if not self.object_view.in_tree((s, patch_display)):
                self.object_view.insert((s, patch_display), patch_display)

    def show_autoplace_marker(self, x, y):
        from gi.repository import Clutter
        if self.autoplace_marker is None:
            self.autoplace_marker = Clutter.Text()
            self.autoplace_marker.set_text("+")
            self.autoplace_layer = self.selected_layer
            self.autoplace_layer.group.add_actor(self.autoplace_marker)
        elif self.autoplace_layer != self.selected_layer:
            if self.autoplace_layer.group:
                self.autoplace_layer.group.remove_actor(self.autoplace_marker)
            self.autoplace_layer = self.selected_layer
            self.autoplace_layer.group.add_actor(self.autoplace_marker)
        self.autoplace_marker.set_position(x, y)
        self.autoplace_marker.set_depth(-10)
        self.autoplace_marker.show()

    def hide_autoplace_marker(self):
        if self.autoplace_marker:
            self.autoplace_marker.hide()

    def grab_focus(self):
        from gi.repository import GObject

        def cb(*args):
            self.embed.grab_focus()

        GObject.timeout_add(10, cb)

    def _init_input(self):
        from gi.repository import Pango

        def resize_cb(widget, rect):
            try:
                self.stage.set_size(rect.width, rect.height)
                if self.hud_mode_text:
                    self.hud_mode_text.set_position(
                        self.stage.get_width()-80, self.stage.get_height()-25
                    )

                if self.cmd_prompt:
                    self.cmd_prompt.set_position(10, self.stage.get_height() - 25)

                    if self.cmd_input:
                        self.cmd_input.set_position(
                            15 + self.cmd_prompt.get_width(), self.stage.get_height() - 25
                        )
            except Exception as e:
                log.error("Error handling resize event", e)
                log.debug(e)
                log.debug_traceback(e)

            return False

        self.grab_focus()

        self.embed.connect('size-allocate', resize_cb)

        self.stage.connect('key-press-event', repeat_event(self, "key-press-event"))
        self.stage.connect('key-release-event', repeat_event(self, "key-release-event"))
        self.stage.connect('button-press-event', repeat_event(self, "button-press-event"))
        self.stage.connect('button-release-event', repeat_event(self, "button-release-event"))
        self.stage.connect('motion-event', repeat_event(self, "motion-event"))
        self.stage.connect('scroll-event', repeat_event(self, "scroll-event"))
        self.stage.connect('enter-event', repeat_event(self, "enter-event"))
        self.stage.connect('leave-event', repeat_event(self, "leave-event"))
        self.stage.connect('destroy', repeat_event(self, "quit"))

        # set tab stops on keybindings view
        ta = Pango.TabArray.new(1, True)
        ta.set_tab(0, Pango.TabAlign.LEFT, 120)
        self.builder.get_object("key_bindings_text").set_tabs(ta)

        self.input_mgr.pointer_x, self.input_mgr.pointer_y = self.embed.get_pointer()

        # show keybindings
        self.display_bindings()

    def console_activate(self):
        alloc = self.content_console_pane.get_allocation()
        oldpos = self.content_console_pane.get_position()

        console_visible = oldpos < (alloc.height - 2)
        if not console_visible:
            next_pos = self.input_mgr.global_mode.previous_console_position
            self.content_console_pane.set_position(next_pos)

        self.bottom_notebook.set_current_page(1)

    def log_write(self, message, level):
        from gi.repository import Gtk

        buf = self.log_view.get_buffer()
        mark = buf.get_mark("log_mark")

        def leader_iters():
            start = buf.get_iter_at_mark(mark)
            start.backward_line()
            start.set_line_offset(0)
            end = buf.get_iter_at_mark(mark)
            end.backward_line()
            end.set_line_offset(0)
            if ']' in message:
                end.forward_chars(message.index(']') + 1)
            return (start, end)

        # this is a bit complicated so that we ensure scrolling is
        # reliable... scroll_to_iter can act odd sometimes

        # find or create tags
        tagtable = buf.get_tag_table()
        monotag = tagtable.lookup("mono")
        warntag = tagtable.lookup("warn")
        errtag = tagtable.lookup("err")
        if monotag is None:
            monotag = buf.create_tag("mono", family="Monospace")
            warntag = buf.create_tag("warn", foreground="#ddaa00", weight=800)
            errtag = buf.create_tag("err", foreground="#770000", weight=700)

        start_it = buf.get_end_iter()
        if mark is None:
            mark = Gtk.TextMark.new("log_mark", False)
            buf.add_mark(mark, start_it)
        buf.insert(start_it, message, -1)

        start_it, end_it = leader_iters()
        buf.apply_tag(monotag, start_it, end_it)

        if level == 1:
            start_it, end_it = leader_iters()
            buf.apply_tag(warntag, start_it, end_it)
        elif level == 2:
            start_it, end_it = leader_iters()
            buf.apply_tag(errtag, start_it, end_it)

        end_it = buf.get_end_iter()
        buf.move_mark(mark, end_it)
        self.log_view.scroll_to_mark(mark, 0, True, 0, 0.9)

    def display_bindings(self):
        from gi.repository import Clutter

        lines = ["Active key/mouse bindings"]
        for m in self.input_mgr.minor_modes:
            lines.append("\nMinor mode: " + m.description)
            for b in m.directory():
                lines.append("%s\t%s" % (b[0], b[1]))

        m = self.input_mgr.major_mode
        lines.append("\nMajor mode: " + m.description)

        if self.hud_mode_text is None:
            self.hud_mode_text = Clutter.Text()
            self.stage.add_actor(self.hud_mode_text)

        self.hud_mode_text.set_position(self.stage.get_width()-80,
                                       self.stage.get_height()-25)
        self.hud_mode_text.set_markup("<b>%s</b>" % m.short_description)

        for b in m.directory():
            lines.append("%s\t%s" % (b[0], b[1]))

        lines.append("\nGlobal bindings:")
        m = self.input_mgr.global_mode
        for b in m.directory():
            lines.append("%s\t%s" % (b[0], b[1]))

        txt = '\n'.join(lines)

        tv = self.builder.get_object("key_bindings_text")
        buf = tv.get_buffer()
        buf.delete(buf.get_start_iter(), buf.get_end_iter())
        buf.insert(buf.get_end_iter(), txt)

    def cmd_set_prompt(self, prompt, default='', space=True, filename=False):
        from gi.repository import Clutter

        if (prompt is None) and self.cmd_input:
            htxt = self.cmd_input.get_text()
            self.cmd_prompt.hide()
            self.cmd_input.hide()
            if htxt:
                self.hud_write(htxt)
            return

        if self.cmd_prompt is None:
            for actor, anim, oldmsg in self.hud_history:
                actor.set_position(actor.get_x(), actor.get_y() - 20)

            self.cmd_prompt = Clutter.Text()
            self.stage.add_actor(self.cmd_prompt)
            self.cmd_prompt.set_position(10, self.stage.get_height() - 25)
            self.cmd_prompt.set_property("opacity", 255)
        else:
            self.cmd_prompt.show()
            self.cmd_input.show()

        self.cmd_prompt.set_markup(prompt)
        self.cmd_input.set_text(default)
        self.cmd_input.set_position(15 + self.cmd_prompt.get_width(),
                                           self.stage.get_height() - 25)

    def hud_write(self, message, disp_time=3.0):
        from gi.repository import Clutter

        def anim_complete(anim):
            new_history = []
            for h_actor, h_anim, h_msg in self.hud_history:
                if anim != h_anim:
                    new_history.append((h_actor, h_anim, h_msg))
                else:
                    h_actor.destroy()
            self.hud_history = new_history

        if len(self.hud_history) == 0 or self.hud_history[0][2] != message:
            for actor, anim, _ in self.hud_history:
                actor.set_position(actor.get_x(), actor.get_y() - 20)
        else:
            self.hud_history[0][1].completed()

        for actor, anim, oldmsg in self.hud_history[3:]:
            anim.completed()

        actor = Clutter.Text()
        self.stage.add_actor(actor)
        if self.cmd_prompt is None:
            actor.set_position(10, self.stage.get_height() - 25)
        else:
            actor.set_position(10, self.stage.get_height() - 45)
        actor.set_property("opacity", 255)
        actor.set_markup(message)

        animation = actor.animatev(Clutter.AnimationMode.EASE_IN_CUBIC,
                                   disp_time * 1000.0, ['opacity'], [0])
        self.hud_history[0:0] = [(actor, animation, message)]
        animation.connect_after("completed", anim_complete)

    def hud_banner(self, msg, disp_time=3.0):
        from gi.repository import Clutter

        def anim_complete(anim, actor):
            actor.destroy()

        if self.hud_banner_anim is not None:
            self.hud_banner_anim.completed()

        self.hud_banner_text = Clutter.Group()
        txt = Clutter.Text()
        bg = Clutter.Rectangle()
        self.hud_banner_text.add_actor(bg)
        self.hud_banner_text.add_actor(txt)

        bg.set_color(ColorDB().find(255, 255, 255, 200))
        bg.set_border_width(1)
        bg.set_border_color(ColorDB().find(0x37, 0x54, 0x50, 0x80))

        self.stage.add_actor(self.hud_banner_text)
        self.hud_banner_text.set_position(12, 4)
        self.hud_banner_text.set_property("opacity", 255)
        txt.set_markup(msg)
        txt.set_position(20, 10)
        bg.set_size(txt.get_width() + 40, txt.get_height() + 20)

        anim = self.hud_banner_text.animatev(Clutter.AnimationMode.EASE_IN_CUBIC,
                                             disp_time * 1000.0, ['opacity'], [0])
        anim.connect_after("completed", anim_complete, self.hud_banner_text)
        self.hud_banner_anim = anim

    def show_selection_box(self, x0, y0, x1, y1):
        if x0 > x1:
            t = x1
            x1 = x0
            x0 = t

        if y0 > y1:
            t = y1
            y1 = y0
            y0 = t

        from gi.repository import Clutter
        if self.selection_box is None:
            self.selection_box = Clutter.Rectangle()
            self.selection_box.set_border_width(1.0)
            self.selection_box.set_color(self.color_transparent)
            self.selection_box.set_border_color(self.color_unselected)
            self.selection_box_layer = self.selected_layer
            self.selection_box_layer.group.add_actor(self.selection_box)
        elif self.selection_box_layer != self.selected_layer:
            self.selection_box_layer.group.remove_actor(self.selection_box)
            self.selection_box_layer = self.selected_layer
            self.selection_box_layer.group.add_actor(self.selection_box)
        self.selection_box.set_position(x0, y0)
        self.selection_box.set_size(max(1, x1-x0), max(1, y1-y0))
        self.selection_box.show()

        enclosed = []
        selection_corners = [(x0, y0), (x1, y0),
                             (x0, y1), (x1, y1)]
        for obj in self.selected_layer.objects:
            if obj.parent_id and MFPGUI().recall(obj.parent_id).parent_id:
                continue
            corners = obj.corners()

            if corners and collision_check(selection_corners, corners):
                enclosed.append(obj)

        return enclosed

    def hide_selection_box(self):
        if self.selection_box:
            self.selection_box.destroy()
            self.selection_box = None

    def clipboard_get(self):
        from gi.repository import Gtk, Gdk
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        return clipboard.wait_for_text()

    def clipboard_set(self, cliptxt):
        from gi.repository import Gtk, Gdk
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        if cliptxt:
            clipboard.set_text(cliptxt, -1)

    def screen_to_canvas(self, x, y):
        if x is None or y is None:
            return (x, y)

        success, new_x, new_y = self.group.transform_stage_point(x, y)
        if success:
            return (new_x, new_y)
        else:
            return (x, y)

    def canvas_to_screen(self, x, y):
        return (
            self.view_x + x / self.zoom,
            self.view_y + y / self.zoom,
        )

    def rezoom(self, **kwargs):
        w, h = self.group.get_size()
        self.group.set_scale_full(self.zoom, self.zoom, w / 2.0, h / 2.0)
        self.group.set_position(self.view_x, self.view_y)
        self.viewport_pos_set = True
        self.viewport_zoom_set = True

    def get_size(self):
        return self.stage.get_size()

    def register(self, element):
        super().register(element)
        if element.container is None:
            if element.layer is None:
                log.debug("WARNING: element has no layer", element, self)
            else:
                element.container = element.layer.group

        if element.group is None:
            log.debug(f"[register] group for {element} is None!!")
        else:
            self.event_sources[element.group] = element
            if hasattr(element, 'texture'):
                self.event_sources[element.texture] = element

        if not isinstance(element, ConnectionElement):
            if not self.load_in_progress:
                self.refresh(element)

    def unregister(self, element):
        super().unregister(element)
        if element.container:
            if isinstance(element.container, BaseElement):
                parent = element.group.get_parent()
                if parent:
                    parent.remove_child(element.group)
            element.container = None

        if isinstance(element, PatchDisplay):
            self.layer_view.remove(element)

        self.object_view.remove(element)
        if element.group in self.event_sources:
            del self.event_sources[element.group]
        if hasattr(element, 'texture') and element.texture in self.event_sources:
            del self.event_sources[element.texture]

    def refresh(self, element):
        if isinstance(element, PatchDisplay):
            for s in element.scopes:
                if not self.object_view.in_tree((s, element)):
                    self.object_view.insert((s, element), element)

            self.object_view.update(element, None)
            self.layer_view.update(element, None)
            return

        if self.load_in_progress:
            return

        if isinstance(element.container, BaseElement):
            self.object_view.update(element, (element.scope, element.container))
        elif element.layer is not None and element.scope is not None:
            self.object_view.update(element, (element.scope, element.layer.patch))
        elif element.layer is not None:
            self.object_view.update(element, (element.layer.scope, element.layer.patch))

    def load_complete(self):
        super().load_complete()
        self.object_view.refresh()
        self.layer_view.refresh()

    def shutdown(self):
        pass

    async def select(self, obj):
        if self.object_view.in_tree(obj):
            self.object_view.select(obj)
        return await AppWindow.select(self, obj)

    async def unselect(self, obj):
        if self.object_view.in_tree(obj):
            self.object_view.unselect(obj)
        return await AppWindow.unselect(self, obj)

    def layer_create(self, layer, patch):
        self.layer_view.insert(layer, patch)

    def layer_select(self, layer):
        AppWindow.layer_select(self, layer)
        self.layer_view.select(layer)

    def layer_update(self, layer, patch):
        self.layer_view.update(layer, patch)

    async def _toggle_console(self, *args):
        alloc = self.content_console_pane.get_allocation()
        oldpos = self.content_console_pane.get_position()

        console_visible = oldpos < (alloc.height - 2)
        if console_visible:
            next_pos = alloc.height
            self.previous_console_position = oldpos
        else:
            next_pos = self.previous_console_position

        self.content_console_pane.set_position(next_pos)

    async def _toggle_info_panel(self, *args):
        def refresh():
            oldpos = self.content_console_pane.get_position()
            self.content_console_pane.set_position(oldpos - 1)
            return False

        from mfp.gui.clutter.utils import clutter_do_later
        oldpos = self.tree_canvas_pane.get_position()

        self.tree_canvas_pane.set_position(self.next_tree_position)
        self.next_tree_position = oldpos

        # KLUDGE!
        clutter_do_later(100, refresh)
