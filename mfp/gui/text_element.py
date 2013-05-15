#! /usr/bin/env python2.6
'''
text_element.py
A text element (comment) in a patch
'''

from gi.repository import Clutter as clutter
from patch_element import PatchElement
from mfp import MFPGUI
from mfp import log
from .modes.label_edit import LabelEditMode


class TextElement (PatchElement):
    display_type = "text"
    proc_type = "text"

    ELBOW_ROOM = 4

    def __init__(self, window, x, y):
        PatchElement.__init__(self, window, x, y)
        self.text = ''

        # configure label
        self.label = clutter.Text()
        self.label.set_use_markup(True)
        self.label.set_color(window.color_unselected)
        self.add_actor(self.label)

        self.update_required = True
        self.set_size(12, 12)
        self.move(x, y)
        self.set_reactive(True)
        self.label_changed_cb = None 


    def update(self):
        if self.label_changed_cb is None: 
            self.label_changed_cb = self.label.connect('text-changed', self.text_changed_cb)

        self.draw_ports()

    def draw_ports(self):
        if self.selected:
            PatchElement.draw_ports(self)

    def label_edit_start(self):
        return self.text

    def label_edit_finish(self, widget, new_text, aborted=False):
        if self.obj_id is None:
            self.create(self.proc_type, None)
        if self.obj_id is None:
            log.debug("TextElement: could not create obj")
        elif new_text != self.text:
            self.text = new_text
            self.label.set_markup(self.text)
            self.set_size(widget.get_width() + self.ELBOW_ROOM,
                          widget.get_height() + self.ELBOW_ROOM)
            MFPGUI().mfp.send(self.obj_id, 0, self.text)
        self.draw_ports()

    def text_changed_cb(self, *args):
        self.set_size(self.label.get_width() + self.ELBOW_ROOM, 
                      self.label.get_height() + self.ELBOW_ROOM)
        self.update()
        return 

    def select(self, *args):
        PatchElement.select(self)
        self.label.set_color(self.stage.color_selected)
        self.draw_ports()

    def unselect(self, *args):
        PatchElement.unselect(self)
        self.label.set_color(self.stage.color_unselected)
        self.hide_ports()

    def make_edit_mode(self):
        return LabelEditMode(self.stage, self, self.label, multiline=True, markup=True)

    def configure(self, params):
        if params.get('value') is not None:
            new_text = params.get('value')
            if new_text != self.text:
                self.text = new_text
                self.label.set_markup(self.text)
                self.set_size(self.label.get_width() + self.ELBOW_ROOM,
                              self.label.get_height() + self.ELBOW_ROOM)
        PatchElement.configure(self, params)
