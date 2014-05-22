#! /usr/bin/env python
'''
patch_window.py
The main MFP window and associated code
'''

from gi.repository import Gtk, Clutter, GtkClutter, Pango

from mfp import MFPGUI
from mfp import log

from .patch_element import PatchElement
from .connection_element import ConnectionElement
from .input_manager import InputManager
from .console import ConsoleMgr
from .prompter import Prompter 
from .colordb import ColorDB
from .modes.global_mode import GlobalMode
from .modes.patch_edit import PatchEditMode
from .modes.patch_control import PatchControlMode
import pkgutil

class PatchWindow(object):
    def __init__(self):
        # load Glade ui
        self.builder = Gtk.Builder()
        self.builder.add_from_string(pkgutil.get_data("mfp.gui", "mfp.glade"))

        # install Clutter stage in Gtk window
        self.window = self.builder.get_object("main_window")
        self.embed = GtkClutter.Embed.new()
        self.embed.set_sensitive(True)
        self.embed.set_size_request(600, 400)
        self.stage = self.embed.get_stage()
        box = self.builder.get_object("stage_box")
        box.pack_start(self.embed, True, True, 0)

        # significant widgets we will be dealing with later
        self.console_view = self.builder.get_object("console_text")
        self.log_view = self.builder.get_object("log_text")
        self.object_view = self.init_object_view()
        self.layer_view = self.init_layer_view()
       
        # objects for stage -- self.group gets moved/scaled to adjust
        # the view, so anything not in it will be static on the stage
        self.group = Clutter.Group()

        # The HUD is the text overlay at the bottom/top of the window that 
        # fades after a short display
        self.hud_history = []
        self.hud_banner_text = None 
        self.hud_banner_anim = None 
        self.hud_prompt = None 
        self.hud_prompt_mgr = Prompter(self)
        self.hud_mode_txt = None 

        self.autoplace_marker = None
        self.autoplace_layer = None
        self.selection_box = None 
        self.selection_box_layer = None 

        self.stage.add_actor(self.group)

        # self.objects is PatchElement subclasses representing the
        # currently-displayed patch(es)
        self.patches = []
        self.objects = []
        self.object_counts_by_type = {}

        self.selected_patch = None
        self.selected_layer = None
        self.selected = []

        self.load_in_progress = False 

        self.input_mgr = InputManager(self)
        self.console_mgr = ConsoleMgr("MFP interactive console", self.console_view)
        self.console_mgr.start()

        # dumb colors
        self.color_unselected = ColorDB().find("default_fg_unsel")
        self.color_transparent = ColorDB().find(255, 255, 255, 0)
        self.color_selected = ColorDB().find("default_fg_sel")
        self.color_bg = ColorDB().find("default_bg")

        # callbacks facility... not yet too much used, but "select" and 
        # "add" are in use 
        self.callbacks = {} 
        self.callbacks_last_id = 0

        # configure Clutter stage
        self.stage.set_color(self.color_bg)
        self.stage.set_property('user-resizable', True)
        self.zoom = 1.0
        self.view_x = 0
        self.view_y = 0

        # show top-level window
        self.stage.show()
        self.window.show_all()

        # set up key and mouse handling
        self.init_input()

    def init_input(self):
        def grab_handler(stage, event):
            if not self.embed.has_focus():
                self.embed.grab_focus()
            return self.input_mgr.handle_event(stage, event)

        def handler(stage, event):
            return self.input_mgr.handle_event(stage, event)

        self.embed.set_can_focus(True)
        self.embed.grab_focus()

        # hook up signals
        self.stage.connect('button-press-event', grab_handler)
        self.stage.connect('button-release-event', grab_handler)
        self.stage.connect('key-press-event', grab_handler)
        self.stage.connect('key-release-event', grab_handler)
        self.stage.connect('destroy', self.quit)
        self.stage.connect('motion-event', handler)
        self.stage.connect('enter-event', handler)
        self.stage.connect('leave-event', handler)
        self.stage.connect('scroll-event', grab_handler)

        # set initial major mode
        self.input_mgr.global_mode = GlobalMode(self)
        self.input_mgr.major_mode = PatchEditMode(self)
        self.input_mgr.major_mode.enable()

        # set tab stops on keybindings view
        ta = Pango.TabArray.new(1, True)
        ta.set_tab(0, Pango.TabAlign.LEFT, 120)
        self.builder.get_object("key_bindings_text").set_tabs(ta)

        self.input_mgr.pointer_x, self.input_mgr.pointer_y = self.embed.get_pointer()

        # show keybindings
        self.display_bindings()

    def load_start(self):
        self.load_in_progress = True 

    def load_complete(self):
        self.load_in_progress = False 
        if self.selected_patch is None and len(self.patches):
            self.selected_patch = self.patches[0]
        if self.selected_layer is None and self.selected_patch is not None:
            self.layer_select(self.selected_patch.layers[0])

    def add_patch(self, patch_info):
        self.patches.append(patch_info)
        self.selected_patch = patch_info
        if len(patch_info.layers):
            self.layer_select(self.selected_patch.layers[0])

    def object_visible(self, obj):
        if obj and hasattr(obj, 'layer'):
            return obj.layer == self.selected_layer
        return True

    def active_layer(self):
        if self.selected_layer is None:
            if self.selected_patch is not None:
                self.layer_select(self.selected_patch.layers[0])

        return self.selected_layer

    def active_group(self):
        return self.active_layer().group

    def ready(self):
        if self.window and self.window.get_realized():
            return True
        else:
            return False

    def stage_pos(self, x, y):
        success, new_x, new_y = self.group.transform_stage_point(x, y)
        if success:
            return (new_x, new_y)
        else:
            return (x, y)

    def display_bindings(self):
        lines = ["Active key/mouse bindings"]
        for m in self.input_mgr.minor_modes:
            lines.append("\nMinor mode: " + m.description)
            for b in m.directory():
                lines.append("%s\t%s" % (b[0], b[1]))

        m = self.input_mgr.major_mode
        lines.append("\nMajor mode: " + m.description)

        if self.hud_mode_txt is None:
            self.hud_mode_txt = Clutter.Text.new()
            self.stage.add_actor(self.hud_mode_txt)
            
        self.hud_mode_txt.set_position(self.stage.get_width()-80,
                                       self.stage.get_height()-25)
        self.hud_mode_txt.set_markup("<b>%s</b>" % m.short_description)

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

    def show_autoplace_marker(self, x, y):
        if self.autoplace_marker is None:
            self.autoplace_marker = Clutter.Text()
            self.autoplace_marker.set_text("+")
            self.autoplace_layer = self.selected_layer
            self.autoplace_layer.group.add_actor(self.autoplace_marker)
        elif self.autoplace_layer != self.selected_layer:
            self.autoplace_layer.group.remove_actor(self.autoplace_marker)
            self.autoplace_layer = self.selected_layer
            self.autoplace_layer.group.add_actor(self.autoplace_marker)
        self.autoplace_marker.set_position(x, y)
        self.autoplace_marker.set_depth(-10)
        self.autoplace_marker.show()

    def hide_autoplace_marker(self):
        if self.autoplace_marker:
            self.autoplace_marker.hide()

    def edit_major_mode(self):
        for o in self.selected:
            o.end_control()

        if isinstance(self.input_mgr.major_mode, PatchControlMode):
            self.input_mgr.set_major_mode(PatchEditMode(self))
        return True

    def control_major_mode(self):
        for o in self.selected:
            o.end_edit()
            o.begin_control()

        if isinstance(self.input_mgr.major_mode, PatchEditMode):
            self.input_mgr.set_major_mode(PatchControlMode(self))
        return True

    def register(self, element):
        self.objects.append(element)

        oldcount = self.object_counts_by_type.get(element.display_type, 0)
        self.object_counts_by_type[element.display_type] = oldcount + 1
        self.input_mgr.event_sources[element] = element

        if element.container is None:
            if element.layer is None:
                print "WARNING: element has no layer", element, self
            else: 
                element.layer.group.add_actor(element)
                element.container = element.layer.group
       
        if not isinstance(element, ConnectionElement):
            if isinstance(element.container, PatchElement):
                self.object_view.insert(element, element.container)
            else: 
                self.object_view.insert(element, (element.layer.scope, element.layer.patch))
        if element.obj_id is not None:
            element.send_params()

        self.emit_signal("add", element)

    def unregister(self, element):
        if element in self.selected:
            self.unselect(element)
        if element.layer:
            element.layer.remove(element)
        if element in self.objects:
            self.objects.remove(element)
        if element in self.input_mgr.event_sources: 
            del self.input_mgr.event_sources[element]

        if element.container: 
            element.container.remove_actor(element)
            element.container = None 

        self.object_view.remove(element)

        self.emit_signal("remove", element)

    def refresh(self, element):
        from .patch_info import PatchInfo
        if isinstance(element, PatchInfo): 
            self.object_view.update(element, None)
            self.layer_view.update(element, None)
            return 

        if element.layer is not None:
            self.object_view.update(element, (element.layer.scope, element.layer.patch))
        else:
            print "WARNING: element has no layer,", element 

    def add_element(self, factory, x=None, y=None):
        if x is None:
            x = self.input_mgr.pointer_x
        if y is None:
            y = self.input_mgr.pointer_y

        b = factory(self, x, y)

        self.active_layer().add(b)
        self.register(b) 
        self.refresh(b)
        self.select(b)

        b.begin_edit()
        return True

    def quit(self, *rest):
        from .patch_info import PatchInfo
        log.debug("Quit command from GUI or WM")

        for p in self.patches:
            if p.deletable:
                p.delete()

        allpatches = MFPGUI().mfp.open_patches()
        guipatches = [ p.obj_id for p in self.objects if isinstance(p, PatchInfo) ]

        for a in allpatches: 
            if a not in guipatches:
                log.debug("Some patches cannot be deleted, not quitting")
                return False 

        if self.console_mgr:
            self.console_mgr.quitreq = True
            self.console_mgr.join()
            log.debug("Console thread reaped")
            self.console_mgr = None 

        MFPGUI().mfp.quit()
        return True

    def console_write(self, msg):
        buf = self.console_view.get_buffer()
        iterator = buf.get_end_iter()
        mark = buf.get_mark("console_mark")
        if mark is None:
            mark = Gtk.TextMark.new("console_mark", False)
            buf.add_mark(mark, iterator)

        buf.insert(iterator, msg, -1)
        iterator = buf.get_end_iter()
        buf.move_mark(mark, iterator)
        self.console_view.scroll_to_mark(mark, 0, True, 1.0, 0.9)

    def log_write(self, msg, level):
        buf = self.log_view.get_buffer()
        mark = buf.get_mark("log_mark")

        def leader_iters(): 
            start = buf.get_iter_at_mark(mark)
            start.backward_line()
            start.set_line_offset(0)
            end = buf.get_iter_at_mark(mark)
            end.backward_line()
            end.set_line_offset(0)
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

    def get_prompted_input(self, prompt, callback, default=''): 
        self.hud_prompt_mgr.get_input(prompt, callback, default)

    def hud_set_prompt(self, prompt, default=''):
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
            self.hud_prompt_input = Clutter.Text()
            self.stage.add_actor(self.hud_prompt)
            self.hud_prompt.set_position(10, self.stage.get_height() - 25)
            self.hud_prompt.set_property("opacity", 255)
            self.stage.add_actor(self.hud_prompt_input)
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
        def anim_complete(anim):
            new_history = []
            for h_actor, h_anim, h_msg in self.hud_history:
                if anim != h_anim:
                    new_history.append((h_actor, h_anim, h_msg))
                else:
                    h_actor.destroy()
            self.hud_history = new_history

        if not len(self.hud_history) or self.hud_history[0][2] != msg:
            for actor, anim, oldmsg in self.hud_history:
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

        self.stage.add_actor(self.hud_banner_text)
        self.hud_banner_text.set_position(12, 4)
        self.hud_banner_text.set_property("opacity", 255)
        txt.set_markup(msg)
        bg.set_size(self.hud_banner_text.get_width(), self.hud_banner_text.get_height())

        anim = self.hud_banner_text.animatev(Clutter.AnimationMode.EASE_IN_CUBIC,
                                             disp_time * 1000.0, ['opacity'], [0])
        anim.connect_after("completed", anim_complete, self.hud_banner_text)
        self.hud_banner_anim = anim

    #####################
    # callbacks
    #####################

    def add_callback(self, signal_name, callback): 
        cbid = self.callbacks_last_id
        self.callbacks_last_id += 1

        oldlist = self.callbacks.setdefault(signal_name, [])
        oldlist.append((cbid, callback))

        return cbid

    def remove_callback(self, cb_id):
        for signal, hlist in self.callbacks.items():
            for num, cbinfo in enumerate(hlist):
                if cbinfo[0] == cb_id:
                    hlist[num:num+1] = [] 
                    return True 
        return False

    def emit_signal(self, signal_name, *args):
        for cbinfo in self.callbacks.get(signal_name, []):
            cbinfo[1](*args)


        
# additional methods in @extends wrappers
import patch_window_layer
import patch_window_views 
import patch_window_select 

