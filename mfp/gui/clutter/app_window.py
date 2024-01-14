"""
clutter/app_window.py - Clutter backend for main app window

wrapper object delegates backend-specific methods here
"""

import pkgutil
import sys

from mfp import log
from mfp.gui.collision import collision_check
from mfp.gui.colordb import ColorDB
from mfp.gui.text_widget import TextWidget
from mfp.gui_main import MFPGUI

from ..backend_interfaces import AppWindowBackend

from ..connection_element import ConnectionElement
from ..base_element import BaseElement
from ..patch_display import PatchDisplay

from .event import repeat_event
from .tree_display import TreeDisplay


class ClutterAppWindowBackend (AppWindowBackend):
    backend_name = "clutter"
    reversed_attrs = [
        'input_mgr', 'object_counts_by_type', 'selected'
    ]

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

        except Exception:
            log.error("Fatal error during GUI startup")
            log.debug_traceback()
            return

        try:
            self._init_window()

        except Exception as e:
            log.error("Caught GUI exception:", e)
            log.debug_traceback()
            sys.stdout.flush()

    def ready(self):
        if self.window and self.window.get_realized():
            return True
        else:
            return False

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
        self.hud_banner_text = None
        self.hud_banner_anim = None

        self.hud_prompt = None
        self.hud_prompt_input = None
        self.hud_mode_txt = None
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
        self.stage.set_color(self.wrapper.color_bg)
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

        # show top-level window
        self.window.show_all()

        self.async_cb_events = set()

    def _init_object_view(self):
        obj_cols, selected_callback = self.wrapper.init_object_view()
        object_view = TreeDisplay(self.builder.get_object("object_tree"), True, *obj_cols)
        object_view.select_cb = selected_callback
        object_view.unselect_cb = lambda obj: MFPGUI().async_task(self.wrapper._unselect(obj))

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

        self.wrapper.signal_listen("created", on_create)
        self.wrapper.signal_listen("rename", on_rename)

        return object_view

    def _init_layer_view(self):
        layer_cols, selected_callback = self.wrapper.init_layer_view()
        layer_view = TreeDisplay(self.builder.get_object("layer_tree"), False, *layer_cols)
        layer_view.select_cb = selected_callback
        layer_view.unselect_cb = None

        return layer_view

    def show_autoplace_marker(self, x, y):
        from gi.repository import Clutter
        if self.autoplace_marker is None:
            self.autoplace_marker = Clutter.Text()
            self.autoplace_marker.set_text("+")
            self.autoplace_layer = self.wrapper.selected_layer
            self.autoplace_layer.backend.group.add_actor(self.autoplace_marker)
        elif self.autoplace_layer != self.wrapper.selected_layer:
            if self.autoplace_layer.backend.group:
                self.autoplace_layer.backend.group.remove_actor(self.autoplace_marker)
            self.autoplace_layer = self.wrapper.selected_layer
            self.autoplace_layer.backend.group.add_actor(self.autoplace_marker)
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
                if self.hud_mode_txt:
                    self.hud_mode_txt.set_position(
                        self.stage.get_width()-80, self.stage.get_height()-25
                    )

                if self.hud_prompt:
                    self.hud_prompt.set_position(10, self.stage.get_height() - 25)

                if self.hud_prompt_input:
                    self.hud_prompt_input.set_position(
                        15 + self.hud_prompt.get_width(), self.stage.get_height() - 25
                    )
            except Exception as e:
                log.error("Error handling UI event", e)
                log.debug(e)
                log.debug_traceback()

            return False

        self.grab_focus()

        self.embed.connect('size-allocate', resize_cb)

        self.stage.connect('key-press-event', repeat_event(self.wrapper, "key-press-event"))
        self.stage.connect('key-release-event', repeat_event(self.wrapper, "key-release-event"))
        self.stage.connect('button-press-event', repeat_event(self.wrapper, "button-press-event"))
        self.stage.connect('button-release-event', repeat_event(self.wrapper, "button-release-event"))
        self.stage.connect('motion-event', repeat_event(self.wrapper, "motion-event"))
        self.stage.connect('scroll-event', repeat_event(self.wrapper, "scroll-event"))
        self.stage.connect('enter-event', repeat_event(self.wrapper, "enter-event"))
        self.stage.connect('leave-event', repeat_event(self.wrapper, "leave-event"))
        self.stage.connect('destroy', repeat_event(self.wrapper, "quit"))

        # set tab stops on keybindings view
        ta = Pango.TabArray.new(1, True)
        ta.set_tab(0, Pango.TabAlign.LEFT, 120)
        self.builder.get_object("key_bindings_text").set_tabs(ta)

        self.wrapper.input_mgr.pointer_x, self.wrapper.input_mgr.pointer_y = self.embed.get_pointer()

        # show keybindings
        self.display_bindings()

    def console_activate(self):
        alloc = self.content_console_pane.get_allocation()
        oldpos = self.content_console_pane.get_position()

        console_visible = oldpos < (alloc.height - 2)
        if not console_visible:
            next_pos = self.wrapper.input_mgr.global_mode.previous_console_position
            self.content_console_pane.set_position(next_pos)

        self.bottom_notebook.set_current_page(1)

    def log_write(self, msg, level):
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
            if ']' in msg:
                end.forward_chars(msg.index(']') + 1)
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
        buf.insert(start_it, msg, -1)

        start_it, end_it = leader_iters()
        buf.apply_tag(monotag, start_it, end_it)

        if (level == 1):
            start_it, end_it = leader_iters()
            buf.apply_tag(warntag, start_it, end_it)
        elif (level == 2):
            start_it, end_it = leader_iters()
            buf.apply_tag(errtag, start_it, end_it)

        end_it = buf.get_end_iter()
        buf.move_mark(mark, end_it)
        self.log_view.scroll_to_mark(mark, 0, True, 0, 0.9)

    def display_bindings(self):
        from gi.repository import Clutter

        lines = ["Active key/mouse bindings"]
        for m in self.wrapper.input_mgr.minor_modes:
            lines.append("\nMinor mode: " + m.description)
            for b in m.directory():
                lines.append("%s\t%s" % (b[0], b[1]))

        m = self.wrapper.input_mgr.major_mode
        lines.append("\nMajor mode: " + m.description)

        if self.hud_mode_txt is None:
            self.hud_mode_txt = Clutter.Text()
            self.stage.add_actor(self.hud_mode_txt)

        self.hud_mode_txt.set_position(self.stage.get_width()-80,
                                       self.stage.get_height()-25)
        self.hud_mode_txt.set_markup("<b>%s</b>" % m.short_description)

        for b in m.directory():
            lines.append("%s\t%s" % (b[0], b[1]))

        lines.append("\nGlobal bindings:")
        m = self.wrapper.input_mgr.global_mode
        for b in m.directory():
            lines.append("%s\t%s" % (b[0], b[1]))

        txt = '\n'.join(lines)

        tv = self.builder.get_object("key_bindings_text")
        buf = tv.get_buffer()
        buf.delete(buf.get_start_iter(), buf.get_end_iter())
        buf.insert(buf.get_end_iter(), txt)

    def hud_set_prompt(self, prompt, default=''):
        from gi.repository import Clutter

        if (prompt is None) and self.hud_prompt_input:
            htxt = self.hud_prompt_input.get_text()
            self.hud_prompt.hide()
            self.hud_prompt_input.hide()
            if htxt:
                self.hud_write(htxt)
            return

        if self.hud_prompt is None:
            for actor, anim, oldmsg in self.hud_history:
                actor.set_position(actor.get_x(), actor.get_y() - 20)

            self.hud_prompt = Clutter.Text()
            self.hud_prompt_input = TextWidget.build(self)
            self.stage.add_actor(self.hud_prompt)
            self.hud_prompt.set_position(10, self.stage.get_height() - 25)
            self.hud_prompt.set_property("opacity", 255)
        else:
            self.hud_prompt.show()
            self.hud_prompt_input.show()

        self.hud_prompt.set_markup(prompt)
        self.hud_prompt_input.set_text(default)
        self.hud_prompt_input.set_position(15 + self.hud_prompt.get_width(),
                                           self.stage.get_height() - 25)

    def hud_write(self, msg, disp_time=3.0):
        from gi.repository import Clutter

        def anim_complete(anim):
            new_history = []
            for h_actor, h_anim, h_msg in self.hud_history:
                if anim != h_anim:
                    new_history.append((h_actor, h_anim, h_msg))
                else:
                    h_actor.destroy()
            self.hud_history = new_history

        if not len(self.hud_history) or self.hud_history[0][2] != msg:
            for actor, anim, _ in self.hud_history:
                actor.set_position(actor.get_x(), actor.get_y() - 20)
        else:
            self.hud_history[0][1].completed()

        for actor, anim, oldmsg in self.hud_history[3:]:
            anim.completed()

        actor = Clutter.Text()
        self.stage.add_actor(actor)
        if self.hud_prompt is None:
            actor.set_position(10, self.stage.get_height() - 25)
        else:
            actor.set_position(10, self.stage.get_height() - 45)
        actor.set_property("opacity", 255)
        actor.set_markup(msg)

        animation = actor.animatev(Clutter.AnimationMode.EASE_IN_CUBIC,
                                   disp_time * 1000.0, ['opacity'], [0])
        self.hud_history[0:0] = [(actor, animation, msg)]
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
            self.selection_box.set_color(self.wrapper.color_transparent)
            self.selection_box.set_border_color(self.wrapper.color_unselected)
            self.selection_box_layer = self.wrapper.selected_layer
            self.selection_box_layer.backend.group.add_actor(self.selection_box)
        elif self.selection_box_layer != self.wrapper.selected_layer:
            self.selection_box_layer.backend.group.remove_actor(self.selection_box)
            self.selection_box_layer = self.wrapper.selected_layer
            self.selection_box_layer.backend.group.add_actor(self.selection_box)
        self.selection_box.set_position(x0, y0)
        self.selection_box.set_size(max(1, x1-x0), max(1, y1-y0))
        self.selection_box.show()

        enclosed = []
        selection_corners = [(x0, y0), (x1, y0),
                             (x0, y1), (x1, y1)]
        for obj in self.wrapper.selected_layer.objects:
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

    async def clipboard_cut(self, pointer_pos):
        if self.wrapper.selected:
            await self.clipboard_copy(pointer_pos)
            await self.wrapper.delete_selected()
            return True
        return False

    async def clipboard_copy(self, pointer_pos):
        if self.wrapper.selected:
            cliptxt = await MFPGUI().mfp.clipboard_copy(
                pointer_pos,
                [o.obj_id for o in self.wrapper.selected if o.obj_id is not None]
            )
            self.clipboard_set(cliptxt)
            return True
        return False

    async def clipboard_paste(self, pointer_pos=None):
        cliptxt = self.clipboard_get()
        if not cliptxt:
            return False

        newobj = await MFPGUI().mfp.clipboard_paste(
            cliptxt, self.wrapper.selected_patch.obj_id,
            self.wrapper.selected_layer.scope, None
        )

        if newobj is not None:
            await self.wrapper.unselect_all()
            for o in newobj:
                obj = MFPGUI().recall(o)
                if obj is None:
                    return True
                if not isinstance(obj, PatchDisplay):
                    obj.move_to_layer(self.wrapper.selected_layer)
                    if obj not in self.wrapper.selected:
                        await self.wrapper.select(MFPGUI().recall(o))
            return False
        else:
            return False

    def screen_to_canvas(self, x, y):
        success, new_x, new_y = self.group.transform_stage_point(x, y)
        if success:
            return (new_x, new_y)
        else:
            return (x, y)

    def canvas_to_screen(self, x, y):
        return (
            self.wrapper.view_x + x / self.wrapper.zoom,
            self.wrapper.view_y + y / self.wrapper.zoom,
        )

    def rezoom(self):
        w, h = self.group.get_size()
        self.group.set_scale_full(self.wrapper.zoom, self.wrapper.zoom, w / 2.0, h / 2.0)
        self.group.set_position(self.wrapper.view_x, self.wrapper.view_y)

    def register(self, element):
        if element.container is None:
            if element.layer is None:
                log.debug("WARNING: element has no layer", element, self)
            else:
                element.container = element.layer.backend.group

        if element.group is None:
            log.debug(f"[register] group for {element} is None!!")
        else:
            self.wrapper.event_sources[element.group] = element
            if hasattr(element, 'texture'):
                self.wrapper.event_sources[element.texture] = element

        if not isinstance(element, ConnectionElement):
            if not self.wrapper.load_in_progress:
                self.refresh(element)

    def unregister(self, element):
        if element.container:
            if isinstance(element.container, BaseElement):
                element.container.remove(element)
            element.container = None

        self.object_view.remove(element)
        if element.group in self.wrapper.event_sources:
            del self.wrapper.event_sources[element.group]
        if hasattr(element, 'texture') and element.texture in self.wrapper.event_sources:
            del self.wrapper.event_sources[element.texture]

    def refresh(self, element):
        if isinstance(element, PatchDisplay):
            self.object_view.update(element, None)
            self.layer_view.update(element, None)
            return

        if self.wrapper.load_in_progress:
            return

        if isinstance(element.container, BaseElement):
            self.object_view.update(element, (element.scope, element.container))
        elif element.layer is not None and element.scope is not None:
            self.object_view.update(element, (element.scope, element.layer.patch))
        elif element.layer is not None:
            self.object_view.update(element, (element.layer.scope, element.layer.patch))

    def load_complete(self):
        self.object_view.refresh()
        self.layer_view.refresh()

    def shutdown(self):
        pass

    def select(self, obj):
        if self.object_view.in_tree(obj):
            self.object_view.select(obj)

    def unselect(self, obj):
        if self.object_view.in_tree(obj):
            self.object_view.unselect(obj)

    def layer_new(self, layer, patch):
        self.layer_view.insert(layer, patch)

    def layer_select(self, layer):
        self.layer_view.select(layer)

    def layer_update(self, layer, patch):
        self.layer_view.update(layer, patch)
