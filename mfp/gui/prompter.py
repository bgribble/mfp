#! /usr/bin/env python
'''
prompter.py -- Prompted input manager for MFP patch window 

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

from .modes.label_edit import LabelEditMode

class Prompter (object): 
    def __init__(self, window):
        self.window = window 
        self.queue = [] 
        self.current_prompt = None
        self.current_callback = None 
        self.mode = None 

    def get_input(self, prompt, callback, default): 
        if self.mode is None:
            self._begin(prompt, callback, default)
        else: 
            self.queue.append([prompt, callback, default])

    def _begin(self, prompt, callback, default): 
        self.current_prompt = prompt
        self.current_callback = callback 
        self.window.hud_set_prompt(prompt, default)
        self.mode = LabelEditMode(self.window, self, self.window.hud_prompt_input, 
                                  mode_desc="Prompted input")
        self.window.input_mgr.enable_minor_mode(self.mode) 

    def label_edit_start(self):
        pass

    def label_edit_finish(self, widget, text):
        if self.current_callback and text:
            try: 
                self.current_callback(text)
            except Exception, e: 
                print "Prompter exception in callback:", e
                pass 

    def end_edit(self):
        if self.mode:
            self.window.input_mgr.disable_minor_mode(self.mode)
            self.mode = None 
        self.window.hud_set_prompt(None)
        if len(self.queue): 
            nextitem = self.queue[0]
            self.queue = self.queue[1:]
            self._begin(nextitem[0], nextitem[1], nextitem[2])


