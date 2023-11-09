#! /usr/bin/env python
'''
text_element.py
A text element (comment) in a patch
'''

from gi.repository import Clutter
import cairo

from .base_element import BaseElement
from mfp.gui_main import MFPGUI
from mfp import log
from mfp.utils import catchall

from .modes.label_edit import LabelEditMode
from .modes.clickable import ClickableControlMode
from .colordb import ColorDB
from .text_widget import TextWidget
from .clutter.base_element import ClutterBaseElementBackend


class TextElement (ClutterBaseElementBackend):
    display_type = "text"
    proc_type = "text"

    ELBOW_ROOM = 5

    style_defaults = {
        'fill-color': 'transparent',
        'fill-color:selected': 'transparent',
        'border': False,
        'border-color': 'default-stroke-color',
        'canvas-size': None
    }

    def __init__(self, window, x, y):
        BaseElement.__init__(self, window, x, y)
        self.value = ''
        self.clickchange = False
        self.default = ''

        self.param_list.extend(['value', 'clickchange', 'default'])

        self.texture = Clutter.Canvas.new()
        self.texture.connect("draw", self.draw_cb)
        self.group.set_content(self.texture)

        self.label = TextWidget.get_factory()(self)
        self.label.set_color(self.get_color('text-color'))
        self.label.set_font_name(self.get_fontspec())
        self.label.set_position(3, 3)

        self.update_required = True
        self.move(x, y)
        self.set_size(12, 12)
        self.group.set_reactive(True)
        self.label_changed_cb = self.label.signal_listen('text-changed', self.text_changed_cb)

    def update(self):
        if not self.get_style('canvas-size'):
            self.set_size(self.label.get_width() + 2*self.ELBOW_ROOM,
                          self.label.get_height() + self.ELBOW_ROOM)
        self.texture.invalidate()
        self.draw_ports()

    @catchall
    def draw_cb(self, texture, ct, width, height):
        # clear the drawing area
        ct.save()
        ct.set_operator(cairo.OPERATOR_CLEAR)
        ct.paint()
        ct.restore()

        # fill to paint the background
        color = ColorDB().normalize(self.get_color('fill-color'))
        ct.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        ct.rectangle(0, 0, width, height)
        ct.fill()

        if self.clickchange or self.get_style('border'):
            ct.set_line_width(1.0)
            ct.translate(0.5, 0.5)
            ct.set_antialias(cairo.ANTIALIAS_NONE)
            ct.rectangle(0, 0, width-1, height-1)
            color = ColorDB().normalize(self.get_color('border-color'))
            ct.set_source_rgba(color.red, color.green, color.blue, color.alpha)
            ct.stroke()
        return True

    def set_size(self, w, h):
        BaseElement.set_size(self, w, h)

        self.texture.set_size(w, h)
        self.texture.invalidate()

    def draw_ports(self):
        if self.selected:
            BaseElement.draw_ports(self)

    def label_edit_start(self):
        return self.value

    async def label_edit_finish(self, widget, new_text, aborted=False):
        if self.obj_id is None:
            await self.create(self.proc_type, None)
        if self.obj_id is None:
            log.warning("TextElement: could not create obj")
        elif new_text != self.value and not aborted:
            self.value = new_text
            self.set_text()
            await MFPGUI().mfp.send(self.obj_id, 0, self.value)
        self.update()

    async def end_edit(self):
        await BaseElement.end_edit(self)
        self.set_text()

    def text_changed_cb(self, *args):
        self.update()
        return

    def clicked(self):
        def newtext(txt):
            self.value = txt or ''
            self.set_text()
        if self.selected and self.clickchange:
            self.app_window.get_prompted_input("New text:", newtext, self.value)
        return True

    def set_text(self):
        if len(self.value):
            self.label.set_markup(self.value)
        else:
            size_set = self.get_style('canvas-size')
            self.value = self.default or (not size_set and '...') or ''
            self.label.set_markup(self.value)

    def unclicked(self):
        return True

    def select(self, *args):
        BaseElement.select(self)
        self.label.set_color(self.get_color('text-color'))
        self.texture.invalidate()
        self.draw_ports()

    def unselect(self, *args):
        BaseElement.unselect(self)
        self.label.set_color(self.get_color('text-color'))
        self.texture.invalidate()
        self.hide_ports()

    async def make_edit_mode(self):
        return LabelEditMode(self.app_window, self, self.label,
                             multiline=True, markup=True, initial=self.value)

    def make_control_mode(self):
        return ClickableControlMode(self.app_window, self, "Change text", 'A-')

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

        newsize = None
        if 'style' in params:
            newstyle = params.get('style')
            if 'canvas-size' in newstyle:
                newsize = newstyle.get('canvas-size')
                params['width'] = newsize[0]
                params['height'] = newsize[1]

        if params.get('border') is not None:
            self.border = params.get('border')

        BaseElement.configure(self, params)
        if newsize:
            self.set_size(*newsize)

        if 'style' in params:
            newstyle = params['style']
            if 'font-face' in newstyle or 'font-size' in newstyle:
                self.label.set_font_name(self.get_fontspec())

        self.update()
