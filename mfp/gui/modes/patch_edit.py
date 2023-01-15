#! /usr/bin/env python
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
from ..slidemeter_element import FaderElement, BarMeterElement, DialElement
from ..via_element import SendViaElement, ReceiveViaElement
from ..via_element import SendSignalViaElement, ReceiveSignalViaElement
from ..button_element import BangButtonElement, ToggleButtonElement, ToggleIndicatorElement

from mfp import log

class PatchEditMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window
        self.autoplace_mode = None
        self.autoplace_x = None
        self.autoplace_y = None
        self.selection_edit_mode = None

        InputMode.__init__(self, "Edit patch", "Edit")
        self.bind('ESC', self.window.control_major_mode, "Exit edit mode")

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
        self.bind("d", lambda: self.add_element(DialElement),
                  "Add dial control")
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


        self.window.add_callback("select", self.selection_changed_cb)
        self.window.add_callback("unselect", self.selection_changed_cb)

    def selection_changed_cb(self, obj):
        if not self.enabled:
            return False

        if self.window.selected:
            self.update_selection_mode()
        else:
            self.disable_selection_mode()

    def add_element(self, factory):
        self.window.unselect_all()
        if self.autoplace_mode is None:
            self.window.add_element(factory)
        else:
            dx = factory.style_defaults.get('autoplace-dx', 0)
            dy = factory.style_defaults.get('autoplace-dy', 0)

            self.window.add_element(factory, self.autoplace_x + dx, self.autoplace_y + dy)
            self.manager.disable_minor_mode(self.autoplace_mode)
            self.autoplace_mode = None

        self.update_selection_mode()
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
        self.update_selection_mode()

    def select_next(self):
        self.window.select_next()
        self.update_selection_mode()
        return True

    def select_prev(self):
        self.window.select_prev()
        self.update_selection_mode()
        return True

    def select_mru(self):
        self.window.select_mru()
        self.update_selection_mode()
        return True

    def update_selection_mode(self):
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

    def disable_selection_mode(self):
        if self.selection_edit_mode is not None:
            self.manager.disable_minor_mode(self.selection_edit_mode)
            self.selection_edit_mode = None
        return True

    def enable(self):
        self.enabled = True
        self.manager.global_mode.allow_selection_drag = True
        self.update_selection_mode()

    def disable(self):
        self.enabled = False
        if self.autoplace_mode:
            self.manager.disable_minor_mode(self.autoplace_mode)
            self.autoplace_mode = None
        self.disable_selection_mode()

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

