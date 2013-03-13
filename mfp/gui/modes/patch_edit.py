#! /usr/bin/env python2.6
'''
patch_edit.py: PatchEdit major mode

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode
from .autoplace import AutoplaceMode
from .selection import SelectionEditMode

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
        self.drag_start_off_x = None
        self.drag_start_off_y = None
        self.drag_target = None
        self.autoplace_mode = None
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
                  "Add send message via")
        self.bind("A-V", lambda: self.add_element(ReceiveSignalViaElement),
                  "Add receive message via")
        
        self.bind("C-n", self.window.layer_new, "Create new layer")
        self.bind("C-N", self.window.layer_new_scope, "Create new layer in a new scope")
        self.bind("C-u", self.window.layer_move_up, "Move current layer up")
        self.bind("C-d", self.window.layer_move_down, "Move current layer down")

        self.bind("TAB", self.select_next, "Select next element")
        self.bind("S-TAB", self.select_prev, "Select previous element")
        self.bind("C-TAB", self.select_mru, "Select most-recent element")

        self.bind("a", self.auto_place_below, "Auto-place below")
        self.bind("A", self.auto_place_above, "Auto-place above")

        self.bind("M1DOWN", self.drag_start, "Select element/start drag")
        self.bind("M1-MOTION", self.drag_selected, "Move element or view")
        self.bind("M1UP", self.drag_end, "Release element/end drag")

        self.bind('+', lambda: self.window.zoom_in(1.25), "Zoom view in")
        self.bind('=', lambda: self.window.zoom_in(1.25), "Zoom view in")
        self.bind('-', lambda: self.window.zoom_out(0.8), "Zoom view out")
        self.bind('SCROLLUP', lambda: self.window.zoom_in(1.06), "Zoom view in")
        self.bind('SCROLLDOWN', lambda: self.window.zoom_in(0.95), "Zoom view out")
        self.bind('C-0', self.window.reset_zoom, "Reset view position and zoom")

    def add_element(self, factory):
        self.enable_selection_edit()
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
        if self.selection_edit_mode is None:
            self.selection_edit_mode = SelectionEditMode(self.window)
            self.manager.enable_minor_mode(self.selection_edit_mode)
        return True

    def disable_selection_edit(self):
        if self.selection_edit_mode is not None:
            self.manager.disable_minor_mode(self.selection_edit_mode)
            self.selection_edit_mode = None
        return True

    def drag_start(self):
        if self.manager.pointer_obj is None:
            self.window.unselect_all()
            self.disable_selection_edit()
        elif self.manager.pointer_obj != self.window.selected:
            self.window.select(self.manager.pointer_obj)
            # self.manager.synthesize("M1DOWN")
            self.enable_selection_edit()

        self.drag_started = True
        if isinstance(self.manager.pointer_obj, ConnectionElement):
            self.drag_target = None
        else:
            self.drag_target = self.manager.pointer_obj

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

    def drag_selected(self):
        if self.drag_started is False:
            return

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
            self.drag_target.drag(dx, dy)
        return True

    def drag_end(self):
        self.drag_started = False
        if self.drag_target:
            self.drag_target.layer.resort(self.drag_target)
            self.drag_target.send_params()
        self.drag_target = None
        return True

    def disable(self):
        if self.autoplace_mode:
            self.manager.disable_minor_mode(self.autoplace_mode)
            self.autoplace_mode = None
