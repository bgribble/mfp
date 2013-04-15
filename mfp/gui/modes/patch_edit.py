#! /usr/bin/env python2.6
'''
patch_edit.py: PatchEdit major mode

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode
from .autoplace import AutoplaceMode
from .selection import SingleSelectionEditMode, MultiSelectionEditMode

from ..text_element import TextElement
from ..processor_element import ProcessorElement
from ..connection_element import ConnectionElement
from ..message_element import MessageElement
from ..enum_element import EnumElement
from ..plot_element import PlotElement
from ..slidemeter_element import FaderElement, BarMeterElement
from ..via_element import SendViaElement, ReceiveViaElement
from ..via_element import SendSignalViaElement, ReceiveSignalViaElement 
from ..button_element import BangButtonElement, ToggleButtonElement, ToggleIndicatorElement


class PatchEditMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window
        self.drag_started = False
        self.selbox_started = False 
        self.selbox_changed = [] 
        self.drag_start_x = None
        self.drag_start_y = None
        self.drag_last_x = None
        self.drag_last_y = None
        self.drag_target = None
        self.autoplace_mode = None
        self.autoplace_x = None 
        self.autoplace_y = None 
        self.selection_edit_mode = None

        InputMode.__init__(self, "Edit patch")

        self.bind("p", lambda: self.add_element(ProcessorElement),
                  "Add processor box")
        self.bind("m", lambda: self.add_element(MessageElement),
                  "Add message box")
        self.bind("n", lambda: self.add_element(EnumElement),
                  "Add number box")
        self.bind("t", lambda: self.add_element(TextElement),
                  "Add text comment")
        self.bind("u", lambda: self.add_element(ToggleButtonElement),
                  "Add toggle button")
        self.bind("g", lambda: self.add_element(BangButtonElement),
                  "Add bang button")
        self.bind("i", lambda: self.add_element(ToggleIndicatorElement),
                  "Add on/off indicator")
        self.bind("s", lambda: self.add_element(FaderElement),
                  "Add slider")
        self.bind("b", lambda: self.add_element(BarMeterElement),
                  "Add bar meter")
        self.bind("x", lambda: self.add_element(PlotElement),
                  "Add X/Y plot")
        self.bind("v", lambda: self.add_element(SendViaElement),
                  "Add send message via")
        self.bind("V", lambda: self.add_element(ReceiveViaElement),
                  "Add receive message via")
        self.bind("A-v", lambda: self.add_element(SendSignalViaElement),
                  "Add send signal via")
        self.bind("A-V", lambda: self.add_element(ReceiveSignalViaElement),
                  "Add receive signal via")
        
        self.bind("C-x", self.cut, "Cut selection to clipboard")
        self.bind("C-c", self.copy, "Copy selection to clipboard")
        self.bind("C-v", self.paste, "Paste clipboard to selection")
        self.bind("C-d", self.duplicate, "Duplicate selection")

        self.bind("C-n", self.window.layer_new, "Create new layer")
        self.bind("C-N", self.window.layer_new_scope, "Create new layer in a new scope")
        self.bind("C-U", self.window.layer_move_up, "Move current layer up")
        self.bind("C-D", self.window.layer_move_down, "Move current layer down")

        self.bind("TAB", self.select_next, "Select next element")
        self.bind("S-TAB", self.select_prev, "Select previous element")
        self.bind("C-TAB", self.select_mru, "Select most-recent element")
        self.bind("C-a", self.select_all, "Select all (in this layer)") 

        self.bind("a", self.auto_place_below, "Auto-place below")
        self.bind("A", self.auto_place_above, "Auto-place above")

        self.bind("M1DOWN", self.drag_start, "Select element/start drag")
        self.bind("M1-MOTION", self.drag_motion, "Move element or view")
        self.bind("M1UP", self.drag_end, "Release element/end drag")

        self.bind("S-M1DOWN", lambda: self.selbox_start(True), "Start selection box")
        self.bind("S-M1-MOTION", lambda: self.selbox_motion(True), "Drag selection box")
        self.bind("S-M1UP", lambda: self.selbox_end(), "End selection box")

        self.bind("C-M1DOWN", lambda: self.selbox_start(False), "Start unselection box")
        self.bind("C-M1-MOTION", lambda: self.selbox_motion(False), "Drag unselection box")
        self.bind("C-M1UP", lambda: self.selbox_end(), "End unselection box")

        self.bind('+', lambda: self.window.zoom_in(1.25), "Zoom view in")
        self.bind('=', lambda: self.window.zoom_in(1.25), "Zoom view in")
        self.bind('-', lambda: self.window.zoom_out(0.8), "Zoom view out")
        self.bind('SCROLLUP', lambda: self.window.zoom_in(1.06), "Zoom view in")
        self.bind('SCROLLDOWN', lambda: self.window.zoom_in(0.95), "Zoom view out")
        self.bind('C-0', self.window.reset_zoom, "Reset view position and zoom")

    def add_element(self, factory):
        self.window.unselect_all()
        if self.autoplace_mode is None:
            self.window.add_element(factory)
        else:
            dx = dy = 0
            if hasattr(factory, "autoplace_dx"):
                dx = factory.autoplace_dx

            if hasattr(factory, "autoplace_dy"):
                dy = factory.autoplace_dy

            self.window.add_element(factory, self.autoplace_x + dx, self.autoplace_y + dy)
            self.manager.disable_minor_mode(self.autoplace_mode)
            self.autoplace_mode = None
        self.enable_selection_edit()
        return True

    def auto_place_below(self):
        self.autoplace_mode = AutoplaceMode(self.window, callback=self.set_autoplace,
                                            initially_below=True)
        self.manager.enable_minor_mode(self.autoplace_mode)
        return True

    def auto_place_above(self):
        self.autoplace_mode = AutoplaceMode(self.window, callback=self.set_autoplace,
                                            initially_below=False)
        self.manager.enable_minor_mode(self.autoplace_mode)
        return True

    def set_autoplace(self, x, y):
        self.autoplace_x = x
        self.autoplace_y = y
        if x is None and y is None:
            self.manager.disable_minor_mode(self.autoplace_mode)
            self.autoplace_mode = None
        return True

    def select_all(self):
        self.window.select_all()
        self.enable_selection_edit()

    def select_next(self):
        self.window.select_next()
        self.enable_selection_edit()
        return True

    def select_prev(self):
        self.window.select_prev()
        self.enable_selection_edit()
        return True

    def select_mru(self):
        self.window.select_mru()
        self.enable_selection_edit()
        return True

    def enable_selection_edit(self):
        if len(self.window.selected) > 1:
            if isinstance(self.selection_edit_mode, SingleSelectionEditMode):
                self.manager.disable_minor_mode(self.selection_edit_mode)
                self.selection_edit_mode = None 
            if not self.selection_edit_mode: 
                self.selection_edit_mode = MultiSelectionEditMode(self.window)
                self.manager.enable_minor_mode(self.selection_edit_mode)
        elif len(self.window.selected) == 1:
            if isinstance(self.selection_edit_mode, MultiSelectionEditMode):
                self.manager.disable_minor_mode(self.selection_edit_mode)
                self.selection_edit_mode = None 
            if not self.selection_edit_mode: 
                self.selection_edit_mode = SingleSelectionEditMode(self.window)
                self.manager.enable_minor_mode(self.selection_edit_mode)

        return True

    def disable_selection_edit(self):
        if self.selection_edit_mode is not None:
            self.manager.disable_minor_mode(self.selection_edit_mode)
            self.selection_edit_mode = None
        return True

    def drag_start(self):
        if self.manager.pointer_obj and self.manager.pointer_obj not in self.window.selected:
            self.window.unselect_all()
            self.window.select(self.manager.pointer_obj)
            self.enable_selection_edit()
            raise self.manager.InputNeedsRequeue()

        self.drag_started = True
        if (self.manager.pointer_obj is None 
            or isinstance(self.manager.pointer_obj, ConnectionElement)):
            self.drag_target = None
        else:
            self.drag_target = self.window.selected

        if self.manager.pointer_obj is None:
            px = self.manager.pointer_ev_x
            py = self.manager.pointer_ev_y
        else:
            px = self.manager.pointer_x
            py = self.manager.pointer_y

        self.drag_start_x = px
        self.drag_start_y = py
        self.drag_last_x = px
        self.drag_last_y = py
        return True

    def drag_motion(self):
        if self.drag_started is False:
            return False 

        if self.drag_target is None:
            px = self.manager.pointer_ev_x
            py = self.manager.pointer_ev_y
        else:
            px = self.manager.pointer_x
            py = self.manager.pointer_y

        dx = px - self.drag_last_x
        dy = py - self.drag_last_y

        self.drag_last_x = px
        self.drag_last_y = py

        if self.drag_target is None:
            self.window.move_view(dx, dy)
        else:
            for obj in self.drag_target:
                obj.drag(dx, dy)
        return True

    def drag_end(self):
        if self.selbox_started:
            self.selbox_end() 

        self.drag_started = False
        if self.drag_target:
            layers = []
            for obj in self.drag_target:
                if obj.layer not in layers: 
                    obj.layer.resort(obj)
                    layers.append(obj.layer)
                obj.send_params()
        else: 
            if self.manager.pointer_obj is None: 
                if (self.manager.pointer_ev_x == self.drag_start_x
                    and self.manager.pointer_ev_y == self.drag_start_y): 
                    self.window.unselect_all()
                    self.disable_selection_edit()

        self.drag_target = None
        return True

    def selbox_start(self, select_mode):
        self.selbox_started = True

        if (self.manager.pointer_obj is not None):
            if self.manager.pointer_obj not in self.window.selected:
                self.window.select(self.manager.pointer_obj)
            elif (not select_mode) and self.manager.pointer_obj in self.window.selected:
                self.window.unselect(self.manager.pointer_obj)

            if self.window.selected:
                self.enable_selection_edit()
            else: 
                self.disable_selection_edit()

        px = self.manager.pointer_x
        py = self.manager.pointer_y

        self.drag_start_x = px
        self.drag_start_y = py
        self.drag_last_x = px
        self.drag_last_y = py
        return True

    def selbox_motion(self, select_mode): 
        if self.selbox_started is False:
            return False 

        px = self.manager.pointer_x
        py = self.manager.pointer_y

        self.drag_last_x = px
        self.drag_last_y = py

        enclosed = self.window.show_selection_box(self.drag_start_x, self.drag_start_y, 
                                                  self.drag_last_x, self.drag_last_y)

        for obj in enclosed:
            if select_mode:
                if obj not in self.window.selected:
                    if obj not in self.selbox_changed:
                        self.selbox_changed.append(obj)
                    self.window.select(obj)
                    self.enable_selection_edit()
            else:
                if obj not in self.selbox_changed:
                    self.selbox_changed.append(obj)
                if obj in self.window.selected:
                    self.window.unselect(obj)
                else: 
                    self.window.select(obj)

            if not self.window.selected:
                self.disable_selection_edit()

        new_changed = []
        for obj in self.selbox_changed: 
            if obj not in enclosed:
                if select_mode:
                    self.window.unselect(obj)
                else: 
                    self.window.select(obj)
            else:
                new_changed.append(obj)
        self.selbox_changed = new_changed 

        return True

    def selbox_end(self):
        self.selbox_started = False
        self.selbox_changed = [] 
        self.window.hide_selection_box()
        return True

    def disable(self):
        if self.autoplace_mode:
            self.manager.disable_minor_mode(self.autoplace_mode)
            self.autoplace_mode = None

    def cut(self):
        return self.window.clipboard_cut((self.manager.pointer_x, 
                                          self.manager.pointer_y))

    def copy(self):
        return self.window.clipboard_copy((self.manager.pointer_x, self.manager.pointer_y))

    def paste(self):
        return self.window.clipboard_paste()

    def duplicate(self):
        self.window.clipboard_copy((self.manager.pointer_x, self.manager.pointer_y))
        return self.window.clipboard_paste()

