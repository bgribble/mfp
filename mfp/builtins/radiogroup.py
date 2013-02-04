#! /usr/bin/env python
'''
radiogroup.py: Manage state of a set of radio buttons

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp


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
        self.hot_inlets = range(num_inlets)

        self.doc_tooltip_inlet = [] 
        self.doc_tooltip_outlet = [] 

        for i in range(num_inlets):
            self.doc_tooltip_inlet.append("Button %d input")
            self.doc_tooltip_outlet.append("Button %d output")

        Processor.__init__(self, num_inlets, num_inlets+1, 
                           init_type, init_args, patch, scope, name)

    def onload(self):
        print "radiogroup: loadbanging", self.init_selection
        for i in range(len(self.inlets)):
            self.send(RGForceFalse(), i)
        self.send(True, self.init_selection)

    def trigger(self):
        for inum, ival in enumerate(self.inlets):
            if ival is Uninit:
                continue
            elif ival is True:
                print "[radiogroup]:", ival, "selecting", inum
                if self.selection is inum:
                    print "[radiogroup]: same selection"
                    continue 
                if self.selection is not None:
                    self.outlets[self.selection] = False 

                self.selection = inum
                self.outlets[self.selection] = True 
                break
            elif (not ival) or isinstance(ival, RGForceFalse): 
                if inum == self.selection: 
                    print "[radiogroup]:", ival, "deselecting", inum
                    self.selection = None 
                if isinstance(ival, RGForceFalse): 
                    self.outlets[inum] = False 
                break
        for inum in range(len(self.inlets)):
            self.inlets[inum] = Uninit
        self.outlets[-1] = self.selection
            
def register():
    MFPApp().register("radiogroup", RadioGroup)
