#! /usr/bin/env python
'''
radiogroup.py: Manage state of a set of radio buttons

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp
from .. import Bang, Uninit
from mfp import log


class RadioGroup (Processor):
    '''
    Processor to manage a set of toggle buttons
    Takes input from each and sends output to the previous
    selection to toggle it off 
    All inlets are hot 
    '''

    def __init__(self, init_type, init_args, patch, scope, name):
        initargs, kwargs = patch.parse_args(init_args)

        num_inlets = initargs[0]
        if len(initargs) > 1:
            init_selection = initargs[1]
        else:
            init_selection = 0

        self.selection = None 
        self.hot_inlets = range(num_inlets)

        Processor.__init__(self, num_inlets, num_inlets, 
                           init_type, init_args, patch, scope, name)
        self.send(True, init_selection)

    def trigger(self):
        for inum, ival in enumerate(self.inlets):
            if ival is Uninit:
                continue
            elif ival:
                if self.selection is not None:
                    self.outlets[self.selection] = False 

                self.selection = inum
                break
            else: 
                if inum == self.selection: 
                    self.selection = None 
                break
        for inum in range(len(self.inlets)):
            self.inlets[inum] = Uninit
            
def register():
    MFPApp().register("radiogroup", RadioGroup)
