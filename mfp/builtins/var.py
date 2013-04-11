#! /usr/bin/env python2.6
'''
p_var.py: Variable holder

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp
from .. import Bang, Uninit
from mfp import log


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

    def __init__(self, init_type, init_args, patch, scope, name):
        self.gui_type = init_type

        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        self.value = Uninit
        self.do_onload = False 


        if len(initargs):
            self.value = initargs[0]
        elif len(kwargs):
            self.value = kwargs

    def onload(self):
        if self.value is not Uninit:
            self.send(Bang)

    def trigger(self):
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
            if (self.inlets[0] is not Bang):
                self.value = self.inlets[0]
                if self.init_type == "text":
                    self.value = str(self.value)
                do_update = True
            self.outlets[0] = self.value
            self.inlets[0] = Uninit

        if do_update and self.gui_params.get("update_required"):
            self.gui_params['value'] = self.value

            if self.gui_created:
                MFPApp().gui_command.configure(self.obj_id, self.gui_params)

    def conf(self, **kwargs):
        for k, v in kwargs.items():
            self.gui_params[k] = v
            if self.gui_created and self.gui_params.get("update_required"):
                MFPApp().gui_command.configure(self.obj_id, self.gui_params)

    def save(self):
        base_dict = Processor.save(self)
        if self.init_type != "message":
            base_dict["value"] = self.value
        return base_dict

    def load(self, params):
        Processor.load(self, params)
        if params.get("value"):
            self.value = params.get("value")
            if self.gui_params.get("value") is None:
                self.gui_params["value"] = self.value
        elif params.get("gui_params").get("value"):
            self.value = params.get("gui_params").get("value")

class Message (Var): 
    doc_tooltip_obj = "Store literal Python data as a message to emit when clicked/triggered"
    doc_tooltip_inlet = ["Emit message on any input", 
                         "Load new message but do not emit" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        Var.__init__(self, init_type, init_args, patch, scope, name)
        self.hot_inlets = (0, 1)

    def trigger(self): 
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
            if self.gui_created:
                MFPApp().gui_command.configure(self.obj_id, self.gui_params)

    def save(self):
        return Processor.save(self)

class Text (Var):
    doc_tooltip_obj = "Comment using SGML-type markup for style"

class Enum (Var):
    doc_tooltip_obj = "Enter and update a numeric message"

    def tooltip(self, port_dir=None, port_num=None):
        if port_dir is not None:
            return Var.tooltip(self, port_dir, port_num)
        else: 
            tt = ('<b>[%s]:</b> ' + self.doc_tooltip_obj ) % self.init_type 
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
                vv = " (%s)" % vv
        return tt + vv


class SlideMeter (Var):
    doc_tooltip_obj = "Display/control a number with a slider"

    def tooltip(self, port_dir=None, port_num=None):
        if port_dir is not None:
            return Var.tooltip(self, port_dir, port_num)
        else: 
            tt = ('<b>[%s]:</b> ' + self.doc_tooltip_obj ) % self.init_type 
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
        return tt + vv
def register():
    MFPApp().register("var", Var)
    MFPApp().register("message", Message)
    MFPApp().register("enum", Enum)
    MFPApp().register("slidemeter", SlideMeter)
    MFPApp().register("text", Text)
