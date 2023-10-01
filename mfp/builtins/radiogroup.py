#! /usr/bin/env python
'''
radiogroup.py: Manage state of a set of radio buttons

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit

class RGForceFalse (object):
    pass

class RadioGroup (Processor):
    '''
    Processor to manage a set of toggle buttons
    Takes input from each and sends output to the previous
    selection to toggle it off
    All inlets are hot
    '''

    doc_tooltip_obj = "Control a radio group of toggle buttons"

    def __init__(self, init_type, init_args, patch, scope, name):
        initargs, kwargs = patch.parse_args(init_args)

        num_inlets = initargs[0]
        if len(initargs) > 1:
            init_selection = initargs[1]
        else:
            init_selection = 0

        self.init_selection = init_selection
        self.selection = None
        self.hot_inlets = list(range(num_inlets))

        self.doc_tooltip_inlet = []
        self.doc_tooltip_outlet = []

        for i in range(num_inlets):
            self.doc_tooltip_inlet.append("Button %(port_num)d input")
            self.doc_tooltip_outlet.append("Button %(port_num)d output")

        Processor.__init__(self, num_inlets, num_inlets+1,
                           init_type, init_args, patch, scope, name)

    async def onload(self, phase):
        if phase == 1:
            for i in range(len(self.inlets)):
                await self.send(RGForceFalse(), i)
            await self.send(True, self.init_selection)

    async def trigger(self):
        for inum, ival in enumerate(self.inlets):
            if ival is Uninit:
                continue
            elif ival is True:
                if self.selection is inum:
                    continue
                if self.selection is not None:
                    self.outlets[self.selection] = False

                self.selection = inum
                self.outlets[self.selection] = True
                break
            elif (not ival) or isinstance(ival, RGForceFalse):
                if inum == self.selection:
                    self.selection = None
                if isinstance(ival, RGForceFalse):
                    self.outlets[inum] = False
                break
        for inum in range(len(self.inlets)):
            self.inlets[inum] = Uninit
        self.outlets[-1] = self.selection

def register():
    MFPApp().register("radiogroup", RadioGroup)
