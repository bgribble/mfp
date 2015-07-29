#! /usr/bin/env python2.6
'''
text_element.py
A text element (comment) in a patch
'''

from gi.repository import Clutter
from patch_element import PatchElement
from mfp import MFPGUI
from mfp import log
from .modes.label_edit import LabelEditMode
from .modes.clickable import ClickableControlMode

class TextElement (PatchElement):
    display_type = "text"
    proc_type = "text"

    ELBOW_ROOM = 5 

    def __init__(self, window, x, y):
        PatchElement.__init__(self, window, x, y)
        self.value = ''
        self.clickchange = False 
        self.default = ''
        self.param_list.extend(['value', 'clickchange', 'default'])

        # configure label
        self.label = Clutter.Text()
        self.label.set_color(window.color_unselected)
        self.add_actor(self.label)

        self.update_required = True
        self.set_size(12, 12)
        self.move(x, y)
        self.set_reactive(True)
        self.label_changed_cb = self.label.connect('text-changed', self.text_changed_cb)


    def update(self):
        self.set_size(self.label.get_width() + 2*self.ELBOW_ROOM, 
                      self.label.get_height() + self.ELBOW_ROOM)
        self.draw_ports()

    def draw_ports(self):
        if self.selected:
            PatchElement.draw_ports(self)

    def label_edit_start(self):
        return self.value

    def label_edit_finish(self, widget, new_text, aborted=False):
        if self.obj_id is None:
            self.create(self.proc_type, None)
        if self.obj_id is None:
            log.warning("TextElement: could not create obj")
        elif new_text != self.value and not aborted:
            self.value = new_text
            self.set_text()
            MFPGUI().mfp.send(self.obj_id, 0, self.value)
        self.update()

    def end_edit(self):
        PatchElement.end_edit(self)
        self.set_text()

    def text_changed_cb(self, *args):
        self.update()
        return 

    def clicked(self):
        def newtext(txt):
            self.value = txt or ''
            self.set_text()
        if self.selected and self.clickchange: 
            self.stage.get_prompted_input("New text:", newtext, self.value)
        return True

    def set_text(self):
        if len(self.value):
            self.label.set_markup(self.value)
        else: 
            self.value = self.default or '...'
            self.label.set_markup(self.value)

    def unclicked(self):
        return True

    def select(self, *args):
        PatchElement.select(self)
        self.label.set_color(self.stage.color_selected)
        self.draw_ports()

    def unselect(self, *args):
        PatchElement.unselect(self)
        self.label.set_color(self.stage.color_unselected)
        self.hide_ports()

    def make_edit_mode(self):
        return LabelEditMode(self.stage, self, self.label, 
                             multiline=True, markup=True, initial=self.value)

    def make_control_mode(self):
        return ClickableControlMode(self.stage, self, "Change text", 'A-')

    def configure(self, params):
        if params.get('value') is not None:
            new_text = params.get('value')
            if new_text != self.value:
                self.value = new_text
                self.set_text()

        if params.get('clickchange') is not None:
            self.clickchange = params['clickchange']

        if params.get('default') is not None:
            self.default = params['default']
        PatchElement.configure(self, params)
        self.update()
