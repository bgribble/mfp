#! /usr/bin/env python2.6
'''
input_manager.py: Handle keyboard and mouse input and route through input modes

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from datetime import datetime, timedelta
import time 

from input_mode import InputMode
from key_sequencer import KeySequencer
from ..quittable_thread import QuittableThread
from ..gui_slave import MFPGUI

class InputManager (object):
    def __init__(self, window):
        self.window = window
        self.global_mode = None
        self.major_mode = None
        self.minor_modes = []
        self.minor_seqno = 0
        self.keyseq = KeySequencer()
        self.event_sources = {}
        self.root_source = None
        self.pointer_x = None
        self.pointer_y = None
        self.pointer_ev_x = None
        self.pointer_ev_y = None
        self.pointer_obj = None
        self.pointer_obj_time = None 
        self.pointer_lastobj = None

        self.hover_thresh=timedelta(microseconds=750000)
        self.hover_mon = QuittableThread(target=self._hover_mon)
        self.hover_mon.start()

    def _hover_mon(self, thread, *rest):
        while not thread.join_req:
            if self.pointer_obj_time is not None:
                elapsed = datetime.now() - self.pointer_obj_time
                if elapsed > self.hover_thresh:
                    MFPGUI().clutter_do(self._hover_handler)
            time.sleep(0.2)

    def _hover_handler(self):
        self.handle_keysym("HOVER")
        return False 
    
    def global_binding(self, key, action, helptext=''):
        self.global_mode.bind(key, action, helptext)

    def set_major_mode(self, mode):
        if isinstance(self.major_mode, InputMode):
            self.major_mode.disable()
        self.major_mode = mode
        self.window.display_bindings()

    def enable_minor_mode(self, mode):
        def modecmp(a, b):
            return cmp(b.affinity, a.affinity) or cmp(b.seqno, a.seqno)

        do_enable = True 
        if mode in self.minor_modes:
            self.minor_modes.remove(mode)
            do_enable = False 
        
        mode.seqno = self.minor_seqno
        self.minor_seqno += 1
        self.minor_modes[:0] = [mode]
        self.minor_modes.sort(cmp=modecmp)
        self.window.display_bindings()
        
        if do_enable:
            mode.enable()

    def disable_minor_mode(self, mode):
        mode.disable()
        self.minor_modes.remove(mode)
        self.window.display_bindings()

    def synthesize(self, key):
        self.keyseq.sequences.append(key)

    def handle_keysym(self, keysym):
        def show_on_hud(keysym, mode, handler):
            mdesc = hdesc = ""
            if mode and mode.description:
                mdesc = mode.description
            if handler and handler[1]:
                hdesc = handler[1]
            if hdesc: 
                self.window.hud_write("%s: %s (%s)" % (keysym, hdesc, mdesc))

        if keysym is not None:
            # check minor modes first
            for minor in self.minor_modes:
                handler = minor.lookup(keysym)
                if handler is not None:
                    show_on_hud(keysym, minor, handler)
                    handled = handler[0]()
                    if handled:
                        return True

            # then major mode
            if self.major_mode is not None:
                handler = self.major_mode.lookup(keysym)
                if handler is not None:
                    show_on_hud(keysym, self.major_mode, handler)
                    handled = handler[0]()
                    if handled:
                        return True

            # then global
            handler = self.global_mode.lookup(keysym)
            if handler is not None:
                show_on_hud(keysym, self.global_mode, handler)
                handled = handler[0]()
                if handled:
                    return True
        return False

    def handle_event(self, stage, event):
        from gi.repository import Clutter
        keysym = None
        if event.type in (
            Clutter.EventType.KEY_PRESS, Clutter.EventType.KEY_RELEASE, Clutter.EventType.BUTTON_PRESS,
                Clutter.EventType.BUTTON_RELEASE, Clutter.EventType.SCROLL):
            self.keyseq.process(event)
            if len(self.keyseq.sequences):
                keysym = self.keyseq.pop()
        elif event.type == Clutter.EventType.MOTION:
            self.pointer_ev_x = event.x
            self.pointer_ev_y = event.y
            self.pointer_x, self.pointer_y = self.window.stage_pos(event.x, event.y)
            self.keyseq.process(event)
            if len(self.keyseq.sequences):
                keysym = self.keyseq.pop()
        elif event.type == Clutter.EventType.ENTER:
            src = self.event_sources.get(event.source)
            #print "ENTER:", src
            if self.window.object_visible(src):
                #print src, "is visible, setting as pointer_obj"
                self.pointer_obj = self.event_sources.get(event.source)
                self.pointer_obj_time = datetime.now()
                if self.pointer_obj == self.pointer_lastobj:
                    self.keyseq.mod_keys = set()
            else:
                #print src, "is not visible"
                pass

        elif event.type == Clutter.EventType.LEAVE:
            src = self.event_sources.get(event.source)
            #print "LEAVE:", src
            if src == self.pointer_obj:
                self.pointer_lastobj = self.pointer_obj
                self.pointer_obj = None
                self.pointer_obj_time = None 
        else:
            return False
        return self.handle_keysym(keysym)

