#! /usr/bin/env python
'''
var.py: Variable holder

Copyright (c) 2010-2015 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp
from .. import Bang, Uninit


class Var (Processor):
    '''
    Processor that holds a single Python value

    Used as the backend for several different GUI elements,
    slightly different behaviors, created with the appropriate name:
    [message], [text], [var], [slider], [enum], [slidemeter]
    '''

    doc_tooltip_obj = "Store a variable message (any type)"
    doc_tooltip_inlet = ["Save input and emit from outlet, or only emit if input is Bang",
                         "Save input but do not emit (default: initarg 0)" ]
    doc_tooltip_outlet = ["Value output"]
    doc_help_patch = "var.help.mfp"

    do_onload = False

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        self.gui_type = init_type

        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)

        self.value = Uninit

        if len(initargs):
            self.value = initargs[0]
        elif len(kwargs):
            self.value = kwargs

    def save_state(self):
        return dict(value=self.value)

    def restore_state(self, state):
        if "value" in state:
            self.value = state["value"]
            if self.init_type == "text":
                self.value = str(self.value)

            # update UI if needed
            if (
                self.gui_params.get("update_required")
                and ('value' not in self.gui_params or self.gui_params['value'] != self.value)
            ):
                self.conf(value=self.value)

            if self.init_type != "message":
                MFPApp().async_task(self.send(Bang))
        return None

    async def onload(self, phase):
        if phase == 1 and self.value is not Uninit:
            await self.send(Bang)

    async def trigger(self):
        '''
        [var] trigger, basic form:
        - on inlet 1, save value but do not output.
          Possibly update GUI display.
        - Bang on inlet 0: output stored value
        - anything else on inlet 0: save and output value
          Possibly update GUI display

        As [text]:
        - ensure that value is a string and save it in the gui_params

        '''
        do_update = False
        if self.inlets[1] is not Uninit:
            self.value = self.inlets[1]
            if self.init_type == "text":
                self.value = str(self.value)
            self.inlets[1] = Uninit
            do_update = True

        if self.inlets[0] is not Uninit:
            # Bang just causes output
            if self.inlets[0] is not Bang:
                self.value = self.inlets[0]
                if self.init_type == "text":
                    self.value = str(self.value)
                do_update = True
            self.outlets[0] = self.value
            self.inlets[0] = Uninit
        if (
            do_update and self.gui_params.get("update_required")
            and ('value' not in self.gui_params or self.gui_params['value'] != self.value)
        ):
            self.conf(value=self.value)
        return True

    def load(self, params):
        Processor.load(self, params)
        if params.get("value"):
            self.value = params.get("value")
            if self.gui_params.get("value") is None:
                self.gui_params["value"] = self.value
        elif params.get("gui_params").get("value"):
            self.value = params.get("gui_params").get("value")

    def tooltip_extra(self):
        dots = ''
        if isinstance(self.value, str):
            vs = '"' + self.value + '"'
        else:
            vs = str(self.value)
        if len(vs) > 30:
            dots = '...'
        return "<b>Value:</b> %s%s" % (vs[:30], dots)


class Message (Var):
    doc_tooltip_obj = "Store literal Python data as a message to emit when clicked/triggered"
    doc_tooltip_inlet = [
        "Emit message on any input",
        "Load new message but do not emit"
    ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Var.__init__(self, init_type, init_args, patch, scope, name, defs)
        self.hot_inlets = (0, 1)

    async def trigger(self):
        do_update = False
        if self.inlets[1] is not Uninit:
            self.value = self.inlets[1]
            self.inlets[1] = Uninit
            do_update = True

        if self.inlets[0] is not Uninit:
            self.outlets[0] = self.value
            self.inlets[0] = Uninit

        if do_update and self.gui_params.get("update_required"):
            self.gui_params['value'] = self.value
            self.conf(value=self.value)


class PatchMessage (Var):
    doc_tooltip_obj = "Store literal Python data as a message to send the patch when clicked/triggered"
    doc_tooltip_inlet = [
        "Emit message on any input",
        "Load new message but do not emit"
    ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Var.__init__(self, init_type, init_args, patch, scope, name, defs)
        self.hot_inlets = (0, 1)

    async def trigger(self):
        do_update = False
        if self.inlets[1] is not Uninit:
            self.value = self.inlets[1]
            self.inlets[1] = Uninit
            do_update = True

        if self.inlets[0] is not Uninit:
            self.outlets[0] = self.value
            self.inlets[0] = Uninit
            await self.patch.send(self.value)

        if do_update and self.gui_params.get("update_required"):
            self.gui_params['value'] = self.value
            self.conf(value=self.value)


class Text (Var):
    doc_tooltip_obj = "Comment using Markdown to style text"

    def save(self):
        base_dict = super().save()
        base_dict["value"] = self.value
        return base_dict


class Enum (Var):
    doc_tooltip_obj = "Enter and update a numeric message"

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Var.__init__(self, init_type, init_args, patch, scope, name, defs)
        self.hot_inlets = (0, 1)

    def save(self):
        base_dict = super().save()
        base_dict["value"] = self.value
        return base_dict

    def tooltip_extra(self):
        minv = self.gui_params.get("min_value")
        maxv = self.gui_params.get("max_value")
        digits = self.gui_params.get("digits", 1)
        ffmt = "%%.%df" % digits

        vv = ''
        if minv is not None or maxv is not None:
            vv = "val"

        if minv is not None:
            vv = (ffmt + " &lt;= ") % minv + vv

        if maxv is not None:
            vv = vv + (" &lt;=" + ffmt) % maxv

        if vv != '':
            vv = "<b>Range:</b> (%s)" % vv
        else:
            vv = None
        return [vv, Var.tooltip_extra(self)]


class SlideMeter (Var):
    doc_tooltip_obj = "Display/control a number with a slider"
    do_onload = True

    def save(self):
        base_dict = super().save()
        base_dict["value"] = self.value
        return base_dict

    def tooltip_extra(self):
        minv = self.gui_params.get("min_value")
        maxv = self.gui_params.get("max_value")
        ffmt = "%.1f"

        vv = ''
        if minv is not None or maxv is not None:
            vv = "val"

        if minv is not None:
            vv = (ffmt + " &lt;= ") % minv + vv

        if maxv is not None:
            vv = vv + (" &lt;=" + ffmt) % maxv

        if vv != '':
            vv = " (%s)" % vv

        return ['<b>Range:</b> ' + vv, Var.tooltip_extra(self)]


def register():
    MFPApp().register("var", Var)
    MFPApp().register("message", Message)
    MFPApp().register("patch_message", PatchMessage)
    MFPApp().register("enum", Enum)
    MFPApp().register("slidemeter", SlideMeter)
    MFPApp().register("text", Text)
