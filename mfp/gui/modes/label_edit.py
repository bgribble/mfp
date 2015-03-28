#! /usr/bin/env python2.6
'''
label_edit.py: Minor mode for editing contents of a clutter.Text label

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import time
from threading import Thread
from ..input_mode import InputMode
from ..colordb import ColorDB 

from mfp.gui_main import clutter_do

def editpoint(s1, s2):
    l1 = len(s1)
    l2 = len(s2)
    if s1 == s2: 
        return None 
    for ept in range(min(l1, l2)):
        if s1[ept] != s2[ept]:
            return ept
    return min(l1, l2)

class Blinker (Thread):
    def __init__(self, txt, blink_time=0.5):
        self.blink_time = 0.5
        self.txt = txt
        self.quitreq = False
        Thread.__init__(self)

    @clutter_do
    def set_cursor(self, val):
        self.txt.set_cursor_visible(val)

    def run(self):
        cursor = True
        while not self.quitreq:
            self.set_cursor(cursor)
            cursor = not cursor
            time.sleep(self.blink_time)


class LabelEditMode (InputMode):
    def __init__(self, window, element, label, multiline=False, markup=False,
                 mode_desc="Edit text", initial=None):
        self.window = window
        self.manager = window.input_mgr
        self.element = element
        self.widget = label
        self.multiline = multiline
        self.markup = markup
        self.text = initial if initial else self.widget.get_text()
        self.cursor_color = ColorDB().find("default_txtcursor") 
        self.undo_stack = [(self.text, len(self.text))]
        self.undo_pos = -1
        self.activate_handler_id = None
        self.text_changed_handler_id = None
        self.key_focus_out_handler_id = None
        self.key_press_handler_id = None
        self.editpos = 0
        self.blinker = None

        InputMode.__init__(self, mode_desc)

        if not self.multiline:
            self.bind("RET", self.commit_edits, "Accept edits")
        else:
            self.bind("C-RET", self.commit_edits, "Accept edits")

        self.bind("ESC", self.rollback_edits, "Discard edits")
        self.bind("LEFT", self.move_left, "Move cursor left")
        self.bind("RIGHT", self.move_right, "Move cursor right")
        self.bind("UP", self.move_up, "Move cursor up one line")
        self.bind("DOWN", self.move_down, "Move cursor down one line")
        self.bind("C-z", self.undo_edit, "Undo typing")
        self.bind("C-r", self.redo_edit, "Redo typing")

        inittxt = self.element.label_edit_start()
        if inittxt:
            self.text = inittxt

        self.update_label(raw=True)
        self.start_editing()
        self.widget.set_selection(0, len(self.text))
       
    def disable(self):
        self.end_editing()
        self.update_label(raw=False)

    def start_editing(self):
        def focus_out(*args): 
            from mfp import log
            log.debug("label-edit: got key-focus-out")
            self.commit_edits()
            return True

        def key_press(widg, event):
            from ..key_defs import KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DN 
            handlers = {KEY_LEFT: self.move_left, KEY_RIGHT: self.move_right, 
                        KEY_UP: self.move_up, KEY_DN: self.move_down}
            keysym = event.keyval
            if keysym in handlers:
                handlers[keysym]()
                return True 
            return False

        def synth_ret(*args):
            self.manager.synthesize("RET")

        if self.multiline is False:
            self.widget.set_single_line_mode(True)
            self.activate_handler_id = self.widget.connect("activate", synth_ret)
        else:
            self.widget.set_single_line_mode(False)
        
        self.text_changed_handler_id = self.widget.connect("text-changed", self.text_changed)
        self.key_focus_out_handler_id = self.widget.connect("key-focus-out", focus_out)
        self.key_press_handler_id = self.window.window.connect("key-press-event", key_press)

        self.editpos = len(self.text)
        self.widget.set_editable(True)
        self.widget.set_cursor_color(self.cursor_color)
        self.widget.set_cursor_visible(True)
        self.update_cursor()

        if self.blinker is not None:
            self.blinker.quitreq = True
            self.blinker.join()
            self.blinker = None

        self.blinker = Blinker(self.widget)
        self.blinker.start()

    def end_editing(self):
        self.widget.set_editable(False)
        self.widget.set_cursor_visible(False)
        if self.activate_handler_id:
            self.widget.disconnect(self.activate_handler_id)
            self.widget.set_activatable(False)
            self.widget.set_single_line_mode(False)
            self.activate_handler_id = None
        if self.key_focus_out_handler_id:
            self.widget.disconnect(self.key_focus_out_handler_id)
            self.key_focus_out_handler_id = None 
        if self.text_changed_handler_id:
            self.widget.disconnect(self.text_changed_handler_id)
            self.text_changed_handler_id = None 
        if self.key_press_handler_id:
            self.window.window.disconnect(self.key_press_handler_id)
            self.key_press_handler_id = None

        if self.blinker is not None:
            self.blinker.quitreq = True
            self.blinker.join()
            self.blinker = None

    def text_changed(self, *args):
        new_text = self.widget.get_text()
        if new_text == self.text:
            return True

        # FIXME - this can be wrong, for example editing fooooo to foooo the 
        # edit point can't be known just from the text change
        change_at = editpoint(self.text, new_text)
        change_dir = len(new_text) - len(self.text)
        if self.undo_pos < -1:
            self.undo_stack[self.undo_pos:] = []
            self.undo_pos = -1

        self.undo_stack.append((self.text, self.editpos))
        self.text = new_text
        
        editpos = self.widget.get_cursor_position()
        if editpos == -1:
            self.editpos = len(self.text)
        elif change_dir > 0:
            self.editpos = change_at + 1
        else: 
            self.editpos = change_at 

        return 

    def commit_edits(self):
        self.text = self.widget.get_text()
        self.end_editing()
        self.update_label(raw=False)
        self.element.label_edit_finish(self.widget, self.text)
        self.element.end_edit()
        return True

    def rollback_edits(self):
        txt, pos = self.undo_stack[0]
        self.text = txt or ''
        self.end_editing()
        self.update_label(raw=False)
        self.element.label_edit_finish(self.widget, self.text)
        self.element.end_edit()
        return True

    def move_to_start(self):
        self.editpos = 0
        self.update_cursor()
        return True 

    def move_to_end(self):
        self.editpos = len(self.text)
        self.update_cursor()
        return True 

    def move_left(self):
        self.editpos = max(self.editpos - 1, 0)
        self.update_cursor()
        return True

    def move_right(self):
        self.editpos = min(self.editpos + 1, len(self.text))
        self.update_cursor()
        return True

    def move_up(self):
        lines_above = self.text[:self.editpos].split("\n")
        line_pos = len(lines_above[-1])
        if len(lines_above) > 2:
            self.editpos = (sum([len(l) + 1 for l in lines_above[:-2]])
                            + min(len(lines_above[-2]), line_pos))
        elif len(lines_above) > 1:
            self.editpos = min(len(lines_above[0]), line_pos)
        else:
            self.editpos = 0  
        self.update_cursor()
        return True

    def move_down(self):
        lines_above = self.text[:self.editpos].split("\n")
        lines_below = self.text[self.editpos:].split("\n")
        line_pos = len(lines_above[-1])
        line_start = self.editpos

        if len(lines_below) > 1:
            self.editpos = (line_start + len(lines_below[0]) + 1
                            + min(len(lines_below[1]), line_pos))
        else:
            self.editpos = len(self.text)
        self.update_cursor()
        return True

    def undo_edit(self):
        if self.undo_pos == -1:
            self.undo_stack.append((self.text, self.editpos))
            self.undo_pos = -2
        if self.undo_pos > (-len(self.undo_stack)):
            self.text, self.editpos = self.undo_stack[self.undo_pos]
            self.undo_pos = max(-len(self.undo_stack), self.undo_pos - 1)
            self.update_label(raw=True)

        return True

    def redo_edit(self):
        if self.undo_pos < -1:
            self.undo_pos += 1
            self.text, self.editpos = self.undo_stack[self.undo_pos]
            self.update_label(raw=True)
        return True

    def update_cursor(self):
        self.widget.grab_key_focus()
        self.widget.set_cursor_position(self.editpos)
        self.widget.set_selection(self.editpos, self.editpos)

    def update_label(self, raw=True):
        if raw or self.markup is False:
            self.widget.set_text(self.text)
            self.widget.set_use_markup(False)
        else:
            self.widget.set_markup(self.text)
        self.update_cursor()
        return True

