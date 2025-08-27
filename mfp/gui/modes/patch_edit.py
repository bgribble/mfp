#! /usr/bin/env python
'''
patch_edit.py: PatchEdit major mode

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from mfp import log
from mfp.gui_main import MFPGUI
from ..input_mode import InputMode
from .autoplace import AutoplaceMode
from .selection import SingleSelectionEditMode, MultiSelectionEditMode

from ..base_element import BaseElement
from ..text_element import TextElement
from ..processor_element import ProcessorElement
from ..message_element import MessageElement, PatchMessageElement
from ..enum_element import EnumElement
from ..plot_element import PlotElement
from ..slidemeter_element import FaderElement, BarMeterElement, DialElement
from ..via_element import SendViaElement, ReceiveViaElement
from ..via_element import SendSignalViaElement, ReceiveSignalViaElement
from ..button_element import BangButtonElement, ToggleButtonElement, ToggleIndicatorElement


class PatchEditMode (InputMode):
    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window
        self.autoplace_mode = None
        self.autoplace_x = None
        self.autoplace_y = None
        self.selection_edit_mode = None

        InputMode.__init__(self, "Edit patch", "Edit")
        self.window.signal_listen("select", self.selection_changed_cb)
        self.window.signal_listen("unselect", self.selection_changed_cb)

    @classmethod
    def init_bindings(cls):
        cls.bind(
            "edit-cut", cls.cut, helptext="Cut selection to clipboard",
            keysym="C-x", menupath="Edit > Cut"
        )
        cls.bind(
            "edit-copy", cls.copy, helptext="Copy selection to clipboard",
            keysym="C-c", menupath="Edit > Copy"
        )
        cls.bind(
            "edit-paste", cls.paste, helptext="Paste clipboard to selection",
            keysym="C-v", menupath="Edit > Paste"
        )
        cls.bind(
            "edit-duplicate", cls.duplicate, helptext="Duplicate selection",
            keysym="C-d", menupath="Edit > Duplicate"
        )
        cls.bind(
            "autoplace-below", cls.auto_place_below, helptext="Auto-place below",
            keysym="a", menupath="Edit > Autoplace below"
        )
        cls.bind(
            "autoplace-above", cls.auto_place_above, helptext="Auto-place above",
            keysym="A", menupath="Edit > Autoplace above"
        )
        cls.bind(
            "add-processor", cls.add_element(ProcessorElement), helptext="Add processor box",
            keysym="p", menupath="Edit > Add element > Processor"
        )
        cls.bind(
            "add-message", cls.add_element(MessageElement), helptext="Add message box",
            keysym="m", menupath="Edit > Add element > Message (data)"
        )
        cls.bind(
            "add-number", cls.add_element(EnumElement), helptext="Add number box",
            keysym="n", menupath="Edit > Add element > Number"
        )
        cls.bind(
            "add-text", cls.add_element(TextElement), helptext="Add text comment",
            keysym="t", menupath="Edit > Add element > Text comment"
        )
        cls.bind(
            "add-toggle", cls.add_element(ToggleButtonElement), helptext="Add toggle button",
            keysym="u", menupath="Edit > Add element > Toggle button"
        )
        cls.bind(
            "add-bang-button", cls.add_element(BangButtonElement), helptext="Add bang button",
            keysym="g", menupath="Edit > Add element > Bang button"
        )
        cls.bind(
            "add-indicator", cls.add_element(ToggleIndicatorElement), helptext="Add on/off indicator",
            keysym="i", menupath="Edit > Add element > Indicator (on/off)"
        )
        cls.bind(
            "add-slider", cls.add_element(FaderElement), helptext="Add slider",
            keysym="s", menupath="Edit > Add element > Slider"
        )
        cls.bind(
            "add-bar-meter", cls.add_element(BarMeterElement), helptext="Add bar meter",
            keysym="b", menupath="Edit > Add element > Bar meter"
        )
        cls.bind(
            "add-dial", cls.add_element(DialElement), helptext="Add dial control",
            keysym="d", menupath="Edit > Add element > Dial"
        )
        cls.bind(
            "add-xyplot", cls.add_element(PlotElement), helptext="Add X/Y plot",
            keysym="x", menupath="Edit > Add element > X/Y plot"
        )
        cls.bind(
            "add-sendvia", cls.add_element(SendViaElement), helptext="Add send message via",
            keysym="v", menupath="Edit > Add element > Send via"
        )
        cls.bind(
            "add-recvvia", cls.add_element(ReceiveViaElement), helptext="Add receive message via",
            keysym="V", menupath="Edit > Add element > Receive via"
        )
        cls.bind(
            "add-sendsigvia", cls.add_element(SendSignalViaElement), helptext="Add send signal via",
            keysym="A-v", menupath="Edit > Add element > Send signal via"
        )
        cls.bind(
            "add-recvsigvia", cls.add_element(ReceiveSignalViaElement), helptext="Add receive signal via",
            keysym="A-V", menupath="Edit > Add element > Receive signal via"
        )
        cls.bind(
            "add-patch-message", cls.add_element(PatchMessageElement), helptext="Add message to patch",
            keysym="%", menupath="Edit > Add element > Message to patch"
        )


        cls.bind(
            "layer-new", lambda mode: mode.window.layer_new(),
            helptext="Create new layer",
            keysym="C-n", menupath="Layer > New layer"
        )
        cls.bind(
            "layer-new-scope", lambda mode: mode.window.layer_new_scope(),
            helptext="Create new layer in a new scope",
            keysym="C-N", menupath="Layer > New layer in new scope"
        )
        cls.bind(
            "layer-move-up", lambda mode: mode.window.layer_move_up(),
            helptext="Move current layer up",
            keysym="A-UP", menupath="Layer > Move layer up"
        )
        cls.bind(
            "layer-move-down", lambda mode: mode.window.layer_move_down(),
            helptext="Move current layer down",
            keysym="A-DOWN", menupath="Layer > Move layer down"
        )

        cls.bind(
            "select-next", cls.select_next, helptext="Select next element",
            keysym="TAB", menupath="Edit > |Select next"
        )
        cls.bind(
            "select-previous", cls.select_prev, helptext="Select previous element",
            keysym="S-TAB", menupath="Edit > |Select previous"
        )
        cls.bind(
            "select-recent", cls.select_mru, helptext="Select most-recent element",
            keysym="C-TAB", menupath="Edit > |Select recent"
        )

        cls.bind(
            "control-mode", cls.control_mode, "Exit edit mode",
            keysym="ESC", menupath="Edit > ||Control mode"
        )

    async def control_mode(self):
        await self.window.control_major_mode()

    def selection_changed_cb(self, window, signal, obj):
        if not self.enabled:
            return False

        if self.window.selected:
            self.update_selection_mode()
        else:
            self.disable_selection_mode()

    @classmethod
    def add_element(cls, element_type):
        async def helper(mode, *args):
            return await mode._add_element(element_type)
        return helper

    def _style_default(self, element_type, style, default=None):
        for c in element_type.mro():
            if hasattr(c, 'style_defaults'):
                if style in c.style_defaults:
                    return c.style_defaults[style]
        return default

    async def _add_element(self, element_type):
        await self.window.unselect_all()
        backend = element_type.get_backend(MFPGUI().backend_name)
        factory = element_type.build
        if self.autoplace_mode is None:
            obj = await self.window.add_element(factory)
        else:
            dx = self._style_default(backend, 'autoplace-dx', 0)
            dy = self._style_default(backend, 'autoplace-dy', 0)

            obj = await self.window.add_element(
                factory,
                self.autoplace_x + dx,
                self.autoplace_y + dy
            )
            port_center = obj.port_center(BaseElement.PORT_IN, 0)
            off = port_center[0] - obj.position_x

            await obj.move(
                obj.position_x - off,
                obj.position_y,
                update_state=True
            )

            self.manager.disable_minor_mode(self.autoplace_mode)
            self.autoplace_mode = None
        if obj:
            await self.window.select(obj)
        self.update_selection_mode()
        return True

    def auto_place_below(self):
        self.autoplace_mode = AutoplaceMode(
            self.window,
            callback=self.set_autoplace,
            initially_below=True
        )
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

    async def select_all(self):
        await self.window.select_all()
        self.update_selection_mode()

    async def select_next(self):
        await self.window.select_next()
        self.update_selection_mode()
        return True

    async def select_prev(self):
        await self.window.select_prev()
        self.update_selection_mode()
        return True

    async def select_mru(self):
        await self.window.select_mru()
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

    async def cut(self):
        return await self.window.clipboard_cut(
            (self.manager.pointer_x, self.manager.pointer_y)
        )

    async def copy(self):
        return await self.window.clipboard_copy((self.manager.pointer_x, self.manager.pointer_y))

    async def paste(self):
        return await self.window.clipboard_paste()

    async def duplicate(self):
        await self.window.clipboard_copy((self.manager.pointer_x, self.manager.pointer_y))
        return await self.window.clipboard_paste()
